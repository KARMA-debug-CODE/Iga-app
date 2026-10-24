"""The accounts app's part of "Download my data" and "Delete my account" (see privacy.py for the convention)."""

from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from apps.core.exporting import iso

from .models import ParentInvite, ParentLink, PasswordResetToken


def export_for(user):
    school = user.school
    return {
        "profile": {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "grade": user.grade,
            "combination": user.combination,
            "preferred_language": user.preferred_language,
            "avatar": user.avatar,
            "xp": user.xp,
            "streak_days": user.streak_days,
            "last_active_date": iso(user.last_active_date),
            "date_joined": iso(user.date_joined),
            "last_login": iso(user.last_login),
            "two_factor_enabled": user.totp_enabled,
            "teacher_approved": user.teacher_approved,
            "school_name_typed": user.school_name,
        },
        "school": (
            {
                "name": school.name,
                "district": school.district,
                "membership": user.school_status,
                "approved_at": iso(user.school_approved_at),
            }
            if school is not None
            else None
        ),
        "terms": {"version": user.terms_version, "accepted_at": iso(user.terms_accepted_at)},
        "deletion": {"requested_at": iso(user.deletion_requested_at), "due_at": iso(user.deletion_due_at)},
        # The people linked to this account, by the name the app shows them.
        "parents": [
            {"name": link.parent.display_name, "linked_at": iso(link.created_at)}
            for link in ParentLink.objects.filter(student=user).select_related("parent")
        ],
        "children": [
            {"name": link.student.display_name, "linked_at": iso(link.created_at)}
            for link in ParentLink.objects.filter(parent=user).select_related("student")
        ],
        "parent_codes": [
            {"created_at": iso(invite.created_at), "expires_at": iso(invite.expires_at), "used": invite.used_by_id is not None}
            for invite in ParentInvite.objects.filter(student=user)
        ],
    }


def erase_for(user):
    """Remove the account's links and secrets, then empty the user row itself. The row stays, as the
    anonymised reference payments, the money ledger and the audit log keep: it can never sign in again."""
    PasswordResetToken.objects.filter(user=user).delete()
    ParentInvite.objects.filter(student=user).delete()
    ParentLink.objects.filter(parent=user).delete()
    ParentLink.objects.filter(student=user).delete()
    OutstandingToken.objects.filter(user=user).delete()  # refresh tokens (and their blacklist entries)

    user.username = f"deleted-{user.pk}"
    user.email = None
    user.first_name = user.last_name = user.school_name = ""
    user.set_unusable_password()
    user.is_active = user.is_staff = user.is_superuser = False
    user.grade = user.combination = ""
    user.avatar = {}
    user.school = None
    user.school_status = ""
    user.school_approved_at = None
    user.school_approved_by = None
    user.teacher_approved_by_school = None
    user.totp_secret = ""
    user.totp_enabled = False
    user.totp_last_step = None
    user.must_change_password = False
    user.temporary_password_expires_at = None
    user.xp = user.streak_days = 0
    user.last_active_date = None
    user.last_login = None
    user.terms_version = ""
    user.terms_accepted_at = None
    user.deletion_due_at = None
    user.erased_at = timezone.now()
    user.save()  # a new (unusable) password: every session ends too
    user.groups.clear()
    user.user_permissions.clear()
