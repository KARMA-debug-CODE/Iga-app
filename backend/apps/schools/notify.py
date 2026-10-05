"""Emails to school administrators about their subscription, each in the administrator's language."""

import logging
from collections import defaultdict

from django.conf import settings
from django.core.mail import send_mail
from django.utils import formats, timezone, translation
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.core.constants import LANGUAGE_CODES

log = logging.getLogger(__name__)


def school_admin_recipients(school):
    """{language: [email, ...]} for the school's approved administrators who have an email."""
    admins = (
        User.objects.filter(school=school, role=User.Role.SCHOOL_ADMIN, school_status=User.SchoolStatus.APPROVED, is_active=True)
        .exclude(email__isnull=True)
        .exclude(email="")
        .values_list("email", "preferred_language")
    )
    recipients = defaultdict(list)
    for email, language in admins:
        recipients[language if language in LANGUAGE_CODES else "en"].append(email)
    return recipients


def _date(value):
    return formats.date_format(timezone.localtime(value), "j F Y") if value else "-"


def _money(amount, currency):
    return f"{formats.number_format(amount, 0 if currency == 'RWF' else 2, use_l10n=True)} {currency}"


def _send(school, compose):
    """Send compose()'s (subject, body), written once per language in that language."""
    sent = 0
    for language, recipients in school_admin_recipients(school).items():
        with translation.override(language):
            subject, body = compose()
        try:
            sent += send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients)
        except Exception:  # an email problem must never break a payment or the daily job
            log.exception("Couldn't email %s about %s", school, subject)
    return sent


def payment_received(payment):
    school = payment.school
    values = {"app": settings.APP_NAME, "school": school.name}

    def compose():
        subject = _("%(app)s: payment received for %(school)s") % values
        body = "\n".join(
            [
                _("Thank you. We received %(amount)s for %(months)s month(s) of %(app)s for %(school)s.")
                % {**values, "amount": _money(payment.amount, payment.currency), "months": payment.months},
                "",
                _("Reference: %(reference)s") % {"reference": payment.reference},
                _("Access paid until: %(date)s") % {"date": _date(school.paid_until)},
                "",
                _("All approved students and teachers of %(school)s have full access.") % values,
                _("Receipts: %(url)s") % {"url": f"{settings.FRONTEND_URL}/school/billing"},
                "",
            ]
        )
        return subject, body

    return _send(school, compose)


def reminder(school, kind):
    days = {"7_days": 7, "3_days": 3, "1_day": 1}.get(kind)
    values = {"app": settings.APP_NAME, "school": school.name}

    def compose():
        if days:
            subject = _("%(app)s: %(school)s's subscription ends in %(days)s day(s)") % {**values, "days": days}
            lead = _("%(school)s's %(app)s subscription is paid until %(date)s.") % {**values, "date": _date(school.paid_until)}
        elif kind == "expired":
            subject = _("%(app)s: %(school)s's subscription has ended") % values
            lead = _(
                "%(school)s's %(app)s subscription ended on %(date)s. Students keep full access until %(grace)s; "
                "after that they will only see the free lessons."
            ) % {**values, "date": _date(school.paid_until), "grace": _date(school.grace_ends())}
        else:
            subject = _("%(app)s: %(school)s's students no longer have full access") % values
            lead = _(
                "%(school)s's %(app)s subscription ended on %(date)s. Students now only see the free lessons "
                "until the school renews."
            ) % {**values, "date": _date(school.paid_until)}
        renew = _("Renew here: %(url)s") % {"url": f"{settings.FRONTEND_URL}/school/billing"}
        return subject, f"{lead}\n\n{renew}\n"

    return _send(school, compose)
