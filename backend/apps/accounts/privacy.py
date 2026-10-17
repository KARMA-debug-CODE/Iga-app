"""The account owner's rights over their data: "Download my data" and "Delete my account".

DATA EXPORT AND DELETION CONVENTION. Every app that stores someone's personal data has a module
`<app>.userdata` with two functions:

    export_for(user) -> dict   JSON-serialisable (plain text, numbers, lists, dicts), only that user's own data
    erase_for(user) -> None    deletes or anonymises that user's rows

Money is never deleted: payments and the append-only ledger keep pointing at the user's row, which stays
as an emptied, anonymised reference ("Deleted account"). This module finds the userdata module of every
installed app (`import "<app>.userdata"` when it exists) and calls them, so a new app only has to add its
own; tests/test_privacy.py fails for an app with a foreign key to users and no userdata module, and checks
that nothing personal is left after an erasure.

Deleting an account (Law N° 058/2021, right to erasure):

1. The owner asks, with a recent password check (step-up), in Profile -> Privacy. A school administrator
   who is the last administrator of a verified school must hand the school over first; Iga team accounts
   are removed by another administrator, not by themselves.
2. Every session ends, and the account is erased ACCOUNT_DELETION_GRACE_DAYS later. Signing in before then
   cancels the deletion (views.LoginView).
3. `manage.py privacy_cleanup` (the scheduler runs it every few minutes) erases the accounts that are due:
   every app's erase_for, in one transaction, the accounts app last (it empties the user row itself).
"""

import importlib
import logging
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import formats, timezone, translation
from django.utils.translation import gettext as _

from apps.core import audit, security_log
from apps.core.constants import LANGUAGE_CODES

from .models import User
from .security import revoke_all_sessions

log = logging.getLogger(__name__)

EXPORT_FORMAT = "iga-personal-data"
EXPORT_FORMAT_VERSION = 1


def userdata_modules():
    """[(app label, module)] for every installed app that has a userdata module, the accounts app last (its
    erase_for empties the user row, which the other apps' erase_for may still read)."""
    found = []
    for config in apps.get_app_configs():
        name = f"{config.name}.userdata"
        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError as error:
            if error.name != name:
                raise  # the app has a userdata module, and it imports something that is missing
            continue
        found.append((config.label, module))
    found.sort(key=lambda item: item[0] == "accounts")
    return found


def export_user_data(user):
    """Everything Iga holds about `user`, app by app (the "Download my data" file)."""
    data = {
        "export": {
            "format": EXPORT_FORMAT,
            "format_version": EXPORT_FORMAT_VERSION,
            "service": settings.APP_NAME,
            "generated_at": timezone.now().isoformat(),
            "user_id": user.pk,
        }
    }
    # Accounts first in the file (who this is), then the apps in the order they are installed.
    modules = userdata_modules()
    for label, module in modules[-1:] + modules[:-1]:
        data[label] = module.export_for(user)
    return data


# --- Deleting an account -------------------------------------------------------------------------------


class DeletionRefused(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def deletion_blocker(user):
    """Why `user` can't ask for their account to be deleted yet, as a DeletionRefused, or None."""
    if user.is_platform_admin:
        return DeletionRefused(
            "platform_admin", _("Iga team accounts are removed by another administrator. Ask them in Admin -> Users.")
        )
    school = user.managed_school
    if school is not None:
        other_admins = (
            User.objects.filter(
                school=school,
                role=User.Role.SCHOOL_ADMIN,
                school_status=User.SchoolStatus.APPROVED,
                is_active=True,
                deletion_due_at__isnull=True,
            )
            .exclude(pk=user.pk)
            .exists()
        )
        if not other_admins:
            return DeletionRefused(
                "transfer_school_first",
                _(
                    "You are the only administrator of %(school)s. Before you delete your account, approve another "
                    "administrator for the school (they sign up and choose it), or ask the Iga team to take it over."
                )
                % {"school": school.name},
            )
    return None


def request_deletion(request, user):
    """Schedule the erasure of `user`'s account and end every session. Returns the time it is due.
    Raises DeletionRefused when deletion_blocker() says so."""
    refusal = deletion_blocker(user)
    if refusal is not None:
        raise refusal
    now = timezone.now()
    due = now + timedelta(days=settings.ACCOUNT_DELETION_GRACE_DAYS)
    User.objects.filter(pk=user.pk).update(deletion_requested_at=now, deletion_due_at=due)
    user.deletion_requested_at, user.deletion_due_at = now, due
    revoke_all_sessions(user)
    security_log.event(request, "account_deletion_requested", user, due=due.isoformat())
    if user.email:
        from .password_reset import deliver

        deliver(_send_safely, _deletion_requested_email, user.email, user.preferred_language, user.username, due)
    return due


def cancel_deletion(request, user):
    """The owner signed in during the grace period: keep the account. True when a deletion was cancelled."""
    cancelled = User.objects.filter(pk=user.pk, deletion_due_at__isnull=False, erased_at__isnull=True).update(
        deletion_requested_at=None, deletion_due_at=None
    )
    if not cancelled:
        return False
    user.deletion_requested_at = user.deletion_due_at = None
    security_log.event(request, "account_deletion_cancelled", user)
    return True


def erase_user(user):
    """Erase or anonymise everything about `user` now, app by app, in one transaction (the money ledger and
    payments stay, pointing at the emptied row). True when it erased the account (False: already erased)."""
    with transaction.atomic():
        locked = User.objects.select_for_update().filter(pk=user.pk).first()
        if locked is None or locked.erased_at is not None:
            return False
        email, language, username = locked.email, locked.preferred_language, locked.username
        for _label, module in userdata_modules():
            module.erase_for(locked)
        audit.record(None, "account_erased", locked)
    if email:
        _send_safely(_erased_email, email, language, username)
    log.info("Erased account %s", user.pk)
    return True


def erase_due_accounts(now=None):
    """Erase every account whose grace period is over (`manage.py privacy_cleanup`). Returns how many."""
    now = now or timezone.now()
    erased = 0
    for user in User.objects.filter(deletion_due_at__lte=now, erased_at__isnull=True).order_by("deletion_due_at"):
        # Signing in at this very moment cancels it: check again on the locked row.
        with transaction.atomic():
            locked = User.objects.select_for_update().filter(pk=user.pk, deletion_due_at__lte=now).first()
            if locked is None:
                continue
            if erase_user(locked):
                erased += 1
    return erased


# --- Emails --------------------------------------------------------------------------------------------


def _language(code):
    return code if code in LANGUAGE_CODES else "en"


def _deletion_requested_email(username, due):
    when = formats.date_format(timezone.localtime(due), "j F Y")
    subject = _("%(app)s: your account will be deleted") % {"app": settings.APP_NAME}
    body = "\n".join(
        [
            _("Hello %(name)s,") % {"name": username},
            "",
            _("You asked us to delete your %(app)s account %(username)s. We will delete it on %(date)s.")
            % {"app": settings.APP_NAME, "username": username, "date": when},
            _("Changed your mind? Just sign in before then and your account stays."),
            "",
            _("If you didn't ask for this, sign in now and change your password."),
            "",
        ]
    )
    return subject, body


def _erased_email(username):
    subject = _("%(app)s: your account has been deleted") % {"app": settings.APP_NAME}
    body = "\n".join(
        [
            _("Hello %(name)s,") % {"name": username},
            "",
            _("Your %(app)s account %(username)s and your personal data have been deleted, as you asked.")
            % {"app": settings.APP_NAME, "username": username},
            _("Thank you for learning with us."),
            "",
        ]
    )
    return subject, body


def _send_safely(compose, email, language, *args):
    try:
        with translation.override(_language(language)):
            subject, body = compose(*args)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email])
    except Exception:  # an email problem must never stop a deletion
        log.exception("Couldn't send an account deletion email")
