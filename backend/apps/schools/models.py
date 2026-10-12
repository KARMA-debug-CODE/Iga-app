import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .constants import DISTRICT_CHOICES

# No 0/O or 1/I: codes are read aloud and copied from a board.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_join_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


class School(models.Model):
    """A secondary school. Its administrators pay one monthly subscription for all its members."""

    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for verification"
        VERIFIED = "verified", "Verified"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=200)
    district = models.CharField(max_length=20, choices=DISTRICT_CHOICES)
    sector = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    # Students who enter it are approved straight away (it proves they were given it by the school).
    join_code = models.CharField(max_length=12, unique=True, default=new_join_code)
    # The subscription is "paid through" this moment. Each payment extends it.
    paid_until = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(Lower("name"), "district", name="unique_school_name_per_district")]

    def __str__(self):
        return f"{self.name} ({self.district})"

    @property
    def is_verified(self):
        return self.status == self.Status.VERIFIED

    def grace_ends(self):
        if self.paid_until is None:
            return None
        return self.paid_until + timedelta(days=settings.SUBSCRIPTION_GRACE_DAYS)

    def subscription_active(self, now=None):
        if not self.is_verified or self.paid_until is None:
            return False
        return (now or timezone.now()) < self.grace_ends()

    def subscription_state(self, now=None):
        """'none' | 'active' | 'grace' (expired but still usable for a few days) | 'expired'."""
        now = now or timezone.now()
        if self.paid_until is None:
            return "none"
        if now < self.paid_until:
            return "active"
        if now < self.grace_ends():
            return "grace"
        return "expired"


class Payment(models.Model):
    class Provider(models.TextChoices):
        FLUTTERWAVE = "flutterwave", "Flutterwave (card / mobile money)"
        MANUAL = "manual", "Recorded by an administrator"
        DEV = "dev", "Test payment (development)"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=64, unique=True)
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="payments")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    months = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    provider_transaction_id = models.CharField(max_length=100, blank=True)
    provider_data = models.JSONField(default=dict, blank=True)
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    # Last time reconcile_payments asked the provider about this payment.
    checked_at = models.DateTimeField(null=True, blank=True)
    # Worked out on the server when the payment is applied (see billing.money_for): what the payer
    # was charged, the provider's fee (from the provider's verified answer) and what reaches Iga.
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    provider_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # A bank transfer or receipt number recorded by the Iga team: each can be recorded only once.
    external_reference = models.CharField(max_length=100, blank=True)
    # The Idempotency-Key of the request that recorded it, so a resent request records nothing new.
    idempotency_key = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # One provider transaction pays for one payment, however it is reported.
            models.UniqueConstraint(
                fields=["provider", "provider_transaction_id"],
                condition=~models.Q(provider_transaction_id=""),
                name="unique_provider_transaction",
            ),
            models.UniqueConstraint(
                fields=["external_reference"], condition=~models.Q(external_reference=""), name="unique_external_reference"
            ),
            models.UniqueConstraint(
                fields=["created_by", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_payment_idempotency_key",
            ),
        ]

    def __str__(self):
        return f"{self.school} · {self.months} month(s) · {self.amount} {self.currency} · {self.status}"


class WebhookEvent(models.Model):
    """Every webhook delivery, accepted or refused: the guard against replays and the trail of refusals.

    A delivery with a valid signature is identified by the SHA-256 of its body, so the same event
    sent again is recognised and not acted on twice (see views.FlutterwaveWebhookView).
    """

    class Outcome(models.TextChoices):
        PROCESSING = "processing", "Being processed"
        APPLIED = "applied", "Payment applied"
        ALREADY_PAID = "already_paid", "Payment was already applied"
        PENDING = "pending", "Not final at the provider yet"
        FAILED = "failed", "Failed or refused at verification"
        UNAVAILABLE = "unavailable", "Provider unreachable; to be retried"
        UNKNOWN_REFERENCE = "unknown_reference", "Not one of our payments"
        NO_REFERENCE = "no_reference", "No payment reference"
        BAD_SIGNATURE = "bad_signature", "Refused: bad or missing signature"
        UNREADABLE = "unreadable", "Refused: unreadable body"

    # Outcomes after which the same delivery may be processed again (the provider retries them).
    RETRYABLE = {Outcome.PROCESSING, Outcome.PENDING, Outcome.UNAVAILABLE}

    provider = models.CharField(max_length=20)
    digest = models.CharField(max_length=64)
    signature_valid = models.BooleanField(default=False)
    reference = models.CharField(max_length=64, blank=True)
    transaction_id = models.CharField(max_length=40, blank=True)
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="webhook_events")
    outcome = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.PROCESSING)
    deliveries = models.PositiveIntegerField(default=1)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "digest"], condition=models.Q(signature_valid=True), name="one_signed_webhook_event"
            )
        ]

    def __str__(self):
        return f"{self.provider} {self.reference or '-'} {self.outcome}"


class LedgerError(Exception):
    """Raised when code tries to change or delete a ledger entry, which is never allowed."""


class LedgerQuerySet(models.QuerySet):
    """Entries are only ever added, through ledger.append; mass updates and deletes are refused."""

    def update(self, **kwargs):
        raise LedgerError("Ledger entries can't be changed; record a correction instead.")

    def delete(self):
        raise LedgerError("Ledger entries can't be deleted; record a correction instead.")

    def bulk_create(self, *args, **kwargs):
        raise LedgerError("Add ledger entries one at a time with ledger.append.")

    def bulk_update(self, *args, **kwargs):
        raise LedgerError("Ledger entries can't be changed; record a correction instead.")

    def update_or_create(self, *args, **kwargs):
        raise LedgerError("Ledger entries can't be changed; record a correction instead.")


class LedgerEntry(models.Model):
    """The money ledger: one row per money event, never changed or deleted.

    Payments, free months, refunds and corrections each add an entry with the money (gross, the
    provider's fee, net) and the change to the school's paid-through date. Each entry carries the
    hash of the previous one, so a changed, removed or reordered entry is detected by
    `manage.py verify_ledger`. On PostgreSQL a trigger refuses UPDATE and DELETE on the table.
    """

    class Kind(models.TextChoices):
        PAYMENT = "payment", "Payment received"
        FREE_MONTHS = "free_months", "Free months"
        REFUND = "refund", "Refund"
        CORRECTION = "correction", "Correction"

    sequence = models.PositiveBigIntegerField(unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="ledger_entries")
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.PROTECT, related_name="ledger_entries")
    corrects = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="corrections")
    currency = models.CharField(max_length=3)
    # Money in (positive) or out (negative, a refund), the provider's fee, and what is left.
    gross_amount = models.DecimalField(max_digits=14, decimal_places=2)
    provider_fee = models.DecimalField(max_digits=14, decimal_places=2)
    net_amount = models.DecimalField(max_digits=14, decimal_places=2)
    # Subscription months added (or removed by a correction), and the paid-through date before and after.
    months = models.SmallIntegerField(default=0)
    paid_until_before = models.DateTimeField(null=True, blank=True)
    paid_until_after = models.DateTimeField(null=True, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    # Who recorded it, copied rather than linked: removing a user must never touch the ledger.
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    actor_name = models.CharField(max_length=150, blank=True)
    note = models.CharField(max_length=300, blank=True)
    idempotency_key = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField()
    hash_alg = models.CharField(max_length=16)
    prev_hash = models.CharField(max_length=64)
    entry_hash = models.CharField(max_length=64, unique=True)

    objects = LedgerQuerySet.as_manager()

    class Meta:
        ordering = ["sequence"]
        verbose_name_plural = "ledger entries"
        constraints = [
            models.UniqueConstraint(fields=["prev_hash"], name="one_ledger_successor"),
            models.UniqueConstraint(
                fields=["actor_user_id", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_ledger_idempotency_key",
            ),
        ]

    def __str__(self):
        return f"#{self.sequence} {self.kind} {self.gross_amount} {self.currency} ({self.school_id})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise LedgerError("Ledger entries can't be changed; record a correction instead.")
        if not getattr(self, "_appending", False):
            raise LedgerError("Add ledger entries with ledger.append.")
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise LedgerError("Ledger entries can't be deleted; record a correction instead.")


class BillingReminder(models.Model):
    """One row per reminder sent, so the daily job never emails the same reminder twice."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="reminders")
    paid_until = models.DateTimeField()
    kind = models.CharField(max_length=20)  # e.g. "7_days", "1_day", "expired"
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["school", "paid_until", "kind"], name="one_reminder_per_period")]
