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

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.school} · {self.months} month(s) · {self.amount} {self.currency} · {self.status}"


class BillingReminder(models.Model):
    """One row per reminder sent, so the daily job never emails the same reminder twice."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="reminders")
    paid_until = models.DateTimeField()
    kind = models.CharField(max_length=20)  # e.g. "7_days", "1_day", "expired"
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["school", "paid_until", "kind"], name="one_reminder_per_period")]
