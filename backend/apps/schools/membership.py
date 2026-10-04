"""Joining a school, and approving or removing members.

Membership unlocks the school's subscription, so it must be confirmed: either the user enters
the school's join code (given out by the school), or a school administrator approves the
request. Platform administrators can do anything a school administrator can.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core import audit

from . import access
from .models import School, new_join_code

JOINING_ROLES = {"student", "teacher", "school_admin"}


def normalise_code(code):
    return (code or "").strip().upper().replace(" ", "").replace("-", "")


def choose_school(user, school, code="", request=None, approved_by=None):
    """Point the user at a school. Approved at once with the right code (or approved_by), else pending.

    Changing school always drops any previous approval. School administrators only join
    through a platform administrator or an existing administrator of that school, never by code.
    """
    if user.role not in JOINING_ROLES:
        raise ValidationError({"school": "Only students, teachers and school staff belong to a school."})
    if school is None:
        return leave_school(user, request=request)
    if not school.is_verified:
        raise ValidationError({"school": "That school isn't verified yet."})
    code_ok = bool(code) and normalise_code(code) == school.join_code and user.role != "school_admin"
    if code and not code_ok and user.role != "school_admin":
        raise ValidationError(
            {
                "school_code": "That code doesn't match this school. Check it with your school, or leave it empty to ask for approval."
            }
        )
    user.school = school
    if code_ok or approved_by is not None:
        _approve(user, approved_by)
    else:
        user.school_status = user.SchoolStatus.PENDING
        user.school_approved_at = None
        user.school_approved_by = None
    user.save(update_fields=["school", "school_status", "school_approved_at", "school_approved_by"])
    access.forget(user)
    if request is not None:
        audit.record(request, "choose_school", user, school=school.id, status=user.school_status, by_code=code_ok)
    return user


def _approve(user, approver):
    user.school_status = user.SchoolStatus.APPROVED
    user.school_approved_at = timezone.now()
    user.school_approved_by = approver


def leave_school(user, request=None):
    old = user.school_id
    user.school = None
    user.school_status = user.SchoolStatus.NONE
    user.school_approved_at = None
    user.school_approved_by = None
    user.save(update_fields=["school", "school_status", "school_approved_at", "school_approved_by"])
    access.forget(user)
    if request is not None and old:
        audit.record(request, "leave_school", user, school=old)
    return user


def can_manage(actor, school):
    if actor.is_platform_admin:
        return True
    return actor.managed_school is not None and actor.managed_school.pk == school.pk


def require_manager(actor, school):
    if not can_manage(actor, school):
        raise PermissionDenied("Only this school's administrators can do that.")


@transaction.atomic
def decide(actor, school, members, approve, request=None):
    """Approve or reject pending requests for `school`. Returns the users changed."""
    require_manager(actor, school)
    changed = []
    for user in members:
        if user.school_id != school.pk or user.school_status != user.SchoolStatus.PENDING:
            continue
        if approve:
            _approve(user, actor)
            fields = ["school_status", "school_approved_at", "school_approved_by"]
            if user.role == "teacher" and not user.teacher_approved:
                # The school vouches for its own teachers.
                user.teacher_approved = True
                fields.append("teacher_approved")
            user.save(update_fields=fields)
        else:
            user.school_status = user.SchoolStatus.REJECTED
            user.save(update_fields=["school_status"])
        access.forget(user)
        changed.append(user)
    if request is not None and changed:
        audit.record(
            request,
            "approve_members" if approve else "reject_members",
            school,
            users=[u.id for u in changed],
        )
    return changed


def remove(actor, school, user, request=None):
    require_manager(actor, school)
    if user.school_id != school.pk:
        raise ValidationError({"user": "That person isn't a member of this school."})
    if user.pk == actor.pk:
        raise ValidationError({"user": "You can't remove yourself."})
    leave_school(user)
    if request is not None:
        audit.record(request, "remove_member", school, user=user.id)


def regenerate_code(actor, school, request=None):
    require_manager(actor, school)
    while True:
        code = new_join_code()
        if not School.objects.filter(join_code=code).exists():
            break
    school.join_code = code
    school.save(update_fields=["join_code"])
    if request is not None:
        audit.record(request, "new_school_code", school)
    return code
