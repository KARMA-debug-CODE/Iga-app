"""Emails to school administrators about their subscription."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import formats, timezone

from apps.accounts.models import User

log = logging.getLogger(__name__)


def school_admin_emails(school):
    return list(
        User.objects.filter(school=school, role=User.Role.SCHOOL_ADMIN, school_status=User.SchoolStatus.APPROVED, is_active=True)
        .exclude(email__isnull=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )


def _date(value):
    return formats.date_format(timezone.localtime(value), "j F Y") if value else "-"


def _send(school, subject, body):
    recipients = school_admin_emails(school)
    if not recipients:
        return 0
    try:
        return send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients)
    except Exception:  # an email problem must never break a payment or the daily job
        log.exception("Couldn't email %s about %s", school, subject)
        return 0


def payment_received(payment):
    school = payment.school
    body = (
        f"Thank you. We received {payment.amount} {payment.currency} for {payment.months} month(s) of "
        f"{settings.APP_NAME} for {school.name}.\n\n"
        f"Reference: {payment.reference}\n"
        f"Access paid until: {_date(school.paid_until)}\n\n"
        f"All approved students and teachers of {school.name} have full access.\n"
        f"Receipts: {settings.FRONTEND_URL}/school/billing\n"
    )
    return _send(school, f"{settings.APP_NAME}: payment received for {school.name}", body)


def reminder(school, kind):
    days = {"7_days": 7, "3_days": 3, "1_day": 1}.get(kind)
    if days:
        subject = f"{settings.APP_NAME}: {school.name}'s subscription ends in {days} day(s)"
        lead = f"{school.name}'s {settings.APP_NAME} subscription is paid until {_date(school.paid_until)}."
    else:
        subject = f"{settings.APP_NAME}: {school.name}'s subscription has ended"
        lead = (
            f"{school.name}'s {settings.APP_NAME} subscription ended on {_date(school.paid_until)}. "
            "Students now only see the free lessons."
        )
    body = f"{lead}\n\nRenew here: {settings.FRONTEND_URL}/school/billing\n"
    return _send(school, subject, body)
