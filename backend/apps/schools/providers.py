"""Payment providers behind one small interface.

A provider turns a pending Payment into a hosted checkout URL, and later says whether the
payment really succeeded by asking the provider's own API (never by trusting what the browser
or a webhook body claims). `billing.apply_payment` does the rest, exactly once.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from .models import Payment


@dataclass
class Verification:
    status: str  # "succeeded" | "failed" | "pending"
    transaction_id: str = ""
    data: dict = field(default_factory=dict)
    # Why a successful transaction was refused: amount_mismatch | currency_mismatch | school_mismatch.
    reason: str = ""
    # From the provider's verified answer: what the payer was charged and the provider's fee.
    gross: Decimal | None = None
    fee: Decimal | None = None


def return_url(payment):
    return f"{settings.FRONTEND_URL}/school/billing/return?ref={payment.reference}"


# An attempt begun just before the session ends can finish a little after it.
CLOSE_MARGIN = timedelta(minutes=15)


def checkout_closed(payment, now=None):
    """True once the hosted checkout for this payment can no longer take a new attempt."""
    now = now or timezone.now()
    return now >= payment.created_at + timedelta(minutes=settings.CHECKOUT_SESSION_MINUTES) + CLOSE_MARGIN


class DevProvider:
    """A fake checkout for local demos and automated tests. Refuses to work unless BILLING_DEV_MODE."""

    key = Payment.Provider.DEV

    def available(self):
        return bool(settings.BILLING_DEV_MODE)

    def create_checkout(self, payment, user, request=None):
        # A page of our own app, so a relative link works whatever host the app is served from.
        return f"/school/billing/dev-checkout?ref={payment.reference}"

    def verify(self, payment, transaction_id=""):
        if not self.available():
            # A test payment is never confirmed on a server where test payments are switched off.
            return Verification("pending")
        outcome = (payment.provider_data or {}).get("dev_outcome")
        if outcome == "success":
            return Verification("succeeded", f"dev-{payment.reference}", {"dev_outcome": outcome})
        if outcome == "cancel":
            return Verification("failed", "", {"dev_outcome": outcome})
        return Verification("pending")


def _registry():
    from .flutterwave import FlutterwaveProvider

    return {Payment.Provider.DEV: DevProvider(), Payment.Provider.FLUTTERWAVE: FlutterwaveProvider()}


def get(key):
    provider = _registry().get(key)
    if provider is None:
        raise ValidationError(_("Unknown payment provider."))
    return provider


def online_provider():
    """The provider schools pay through: the configured one, or the dev checkout in development."""
    registry = _registry()
    configured = registry.get(settings.BILLING_PROVIDER) if settings.BILLING_PROVIDER else None
    if configured is not None and configured.available():
        return configured
    if registry[Payment.Provider.DEV].available():
        return registry[Payment.Provider.DEV]
    return None
