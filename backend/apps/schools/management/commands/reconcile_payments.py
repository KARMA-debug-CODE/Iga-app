"""Re-check online payments that are still open, in case a webhook was lost or the payer closed
the page before coming back. Run it every few minutes, e.g. from the Docker `scheduler` service
or cron: `python manage.py reconcile_payments`.

- A payment the provider now reports as successful is applied (once, as always).
- A payment whose checkout has closed without a successful transaction is marked cancelled.
- Open payments older than BILLING_RECONCILE_DAYS are closed without asking the provider.
- Payments closed in the last CLOSED_RECHECK are asked about again, in case a mobile money approval
  completed after the checkout closed and its webhook never arrived.

Closing a payment never loses money: if the provider later reports a successful transaction for
it (webhook or the return page), billing.apply_payment still applies it.
"""

import logging
from collections import Counter
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.schools import billing, providers
from apps.schools.models import Payment

log = logging.getLogger(__name__)
CLOSED_RECHECK = timedelta(days=1)


def reconcile(now=None):
    now = now or timezone.now()
    counts = Counter()
    open_payments = Payment.objects.filter(status=Payment.Status.PENDING).exclude(provider=Payment.Provider.MANUAL)
    since = now - timedelta(days=settings.BILLING_RECONCILE_DAYS)
    counts["expired"] = open_payments.filter(created_at__lt=since).update(status=Payment.Status.CANCELLED)

    online = Payment.objects.exclude(provider=Payment.Provider.MANUAL)
    to_check = online.filter(status=Payment.Status.PENDING, created_at__gte=since) | online.filter(
        status__in=[Payment.Status.FAILED, Payment.Status.CANCELLED], created_at__gte=now - CLOSED_RECHECK
    )
    for payment in to_check.select_related("school").order_by("created_at"):
        try:
            provider = providers.get(payment.provider)
        except APIException:
            continue
        if not provider.available():
            continue
        try:
            payment = billing.settle(payment, provider.verify(payment))
        except APIException as exc:  # the provider is down: try again next run
            log.warning("Could not re-check payment %s: %s", payment.reference, exc)
            counts["unreachable"] += 1
            continue
        except Exception:  # one odd payment must not stop the others from being reconciled
            log.exception("Unexpected error re-checking payment %s", payment.reference)
            counts["errors"] += 1
            continue
        if payment.status == Payment.Status.PENDING and providers.checkout_closed(payment, now):
            billing.fail_payment(payment, status=Payment.Status.CANCELLED)
            payment.refresh_from_db()
        counts[payment.status] += 1
    return counts


class Command(BaseCommand):
    help = "Re-check open online payments with the provider and close abandoned ones (safe to run often)."

    def handle(self, *args, **options):
        counts = reconcile()
        summary = ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()) if value) or "nothing open"
        self.stdout.write(f"Payments re-checked ({summary}).")
