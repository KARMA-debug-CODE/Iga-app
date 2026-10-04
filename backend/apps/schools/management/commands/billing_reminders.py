"""Email school administrators before and when their subscription ends. Run it once a day,
e.g. `docker compose exec backend python manage.py billing_reminders` from cron."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.schools import notify
from apps.schools.models import BillingReminder, School

# (kind, how long before the end date it is due)
SCHEDULE = [("7_days", timedelta(days=7)), ("3_days", timedelta(days=3)), ("1_day", timedelta(days=1))]


def due_reminders(school, now):
    """The single most urgent reminder that is due now for this school's current end date, or None."""
    if school.paid_until is None:
        return None
    if now >= school.grace_ends():
        # Access has stopped. Only for recent ones, so an old database doesn't email everyone at once.
        return "access_ended" if now - school.grace_ends() < timedelta(days=14) else None
    if now >= school.paid_until:
        return "expired"  # in the grace period: students still have full access
    left = school.paid_until - now
    due = [kind for kind, before in SCHEDULE if left <= before]
    return due[-1] if due else None


class Command(BaseCommand):
    help = "Send subscription reminders to school administrators (idempotent: run daily)."

    def handle(self, *args, **options):
        now = timezone.now()
        sent = 0
        schools = School.objects.filter(status=School.Status.VERIFIED, paid_until__isnull=False)
        for school in schools:
            kind = due_reminders(school, now)
            if kind is None:
                continue
            try:
                with transaction.atomic():
                    BillingReminder.objects.create(school=school, paid_until=school.paid_until, kind=kind)
            except IntegrityError:
                continue  # already sent for this end date
            notify.reminder(school, kind)
            sent += 1
        self.stdout.write(f"Sent {sent} reminder(s).")
