"""School subscriptions: prices, payments and how a payment extends a school's access.

A school is "paid through" `School.paid_until`. A successful payment for N months extends it
by N calendar months, counted from today or from the current end date if that is later, so
renewing early never loses days. Payments are applied exactly once, inside a transaction that
locks the school row, whichever path reports them first (redirect, webhook or an administrator).
"""

import calendar
import secrets
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from .models import Payment, School

# Currencies without a minor unit: prices are whole francs.
ZERO_DECIMAL_CURRENCIES = {"RWF"}


def add_months(moment: datetime, months: int) -> datetime:
    """Same day-of-month N months later, clamped to the month's last day (31 Jan + 1 = 28/29 Feb)."""
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def currencies():
    return list(settings.SUBSCRIPTION_PRICES)


def price(months: int, currency: str) -> Decimal:
    if months not in settings.SUBSCRIPTION_MONTH_OPTIONS:
        raise ValidationError(
            {"months": _("Choose %(options)s months.") % {"options": ", ".join(map(str, settings.SUBSCRIPTION_MONTH_OPTIONS))}}
        )
    if currency not in settings.SUBSCRIPTION_PRICES:
        raise ValidationError(
            {"currency": _("Choose one of these currencies: %(options)s.") % {"options": ", ".join(currencies())}}
        )
    step = Decimal("1") if currency in ZERO_DECIMAL_CURRENCIES else Decimal("0.01")
    return (settings.SUBSCRIPTION_PRICES[currency] * months).quantize(step)


def new_reference():
    return f"iga-{secrets.token_hex(12)}"


def start_payment(school: School, user, months: int, currency: str, provider: str) -> Payment:
    if not school.is_verified:
        raise ValidationError(_("Your school must be verified by the Iga team before it can subscribe."))
    return Payment.objects.create(
        reference=new_reference(),
        school=school,
        created_by=user,
        provider=provider,
        months=months,
        amount=price(months, currency),
        currency=currency,
    )


def apply_payment(payment: Payment, transaction_id: str = "", data: dict | None = None, now=None) -> bool:
    """Mark a payment as paid and extend the school's subscription.

    Only ever called once the provider's own API has confirmed the money arrived (or for a payment
    an administrator recorded), so it also applies to a payment already marked failed or
    cancelled: a success reported late, after the checkout closed, must still give the school its
    months. Returns True if this call applied it, False if it had already been applied.
    """
    now = now or timezone.now()
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status == Payment.Status.SUCCEEDED:
            return False
        school = School.objects.select_for_update().get(pk=payment.school_id)
        start = max(now, school.paid_until) if school.paid_until else now
        # Calendar months in Kigali time: a payment just after midnight belongs to the new day.
        end = add_months(timezone.localtime(start), payment.months)
        school.paid_until = end
        school.save(update_fields=["paid_until"])
        payment.status = Payment.Status.SUCCEEDED
        payment.paid_at = now
        payment.period_start = start
        payment.period_end = end
        if transaction_id:
            payment.provider_transaction_id = str(transaction_id)[:100]
        if data is not None:
            payment.provider_data = data
        payment.save()
    return True


def fail_payment(payment: Payment, status: str = Payment.Status.FAILED, data: dict | None = None) -> bool:
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != Payment.Status.PENDING:
            return False
        payment.status = status
        if data is not None:
            payment.provider_data = data
        payment.save(update_fields=["status", "provider_data"])
    return True


def record_manual_payment(school: School, admin, months: int, amount: Decimal, currency: str, note: str) -> Payment:
    """A platform administrator records money received outside the app (bank transfer, cash,
    mobile money to the company account) or a complimentary extension (amount 0)."""
    if months < 1 or months > 24:
        raise ValidationError({"months": _("Between 1 and 24 months.")})
    if amount < 0:
        raise ValidationError({"amount": _("The amount can't be negative.")})
    if not note.strip():
        raise ValidationError({"note": _("Say how it was paid (bank reference, receipt number, or why it is free).")})
    payment = Payment.objects.create(
        reference=new_reference(),
        school=school,
        created_by=admin,
        provider=Payment.Provider.MANUAL,
        months=months,
        amount=amount,
        currency=currency,
        note=note.strip()[:300],
    )
    apply_payment(payment)
    payment.refresh_from_db()
    return payment


def settle(payment: Payment, verification, request=None) -> Payment:
    """Act on what the provider says about a payment. Safe to call any number of times."""
    from apps.core import audit

    from . import notify

    if verification.status == "succeeded":
        if apply_payment(payment, verification.transaction_id, verification.data):
            payment.refresh_from_db()
            audit.record(
                request,
                "subscription_paid",
                payment.school,
                reference=payment.reference,
                months=payment.months,
                amount=str(payment.amount),
                currency=payment.currency,
                provider=payment.provider,
            )
            notify.payment_received(payment)
    elif verification.status == "failed":
        fail_payment(payment, data=verification.data)
    payment.refresh_from_db()
    return payment
