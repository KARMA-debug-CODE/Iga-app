"""Joining a school, and approving or removing members.

Membership unlocks the school's subscription, so it must be confirmed: either the user enters
the school's join code (given out by the school), or a school administrator approves the
request. Platform administrators can do anything a school administrator can.
"""

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
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
        raise ValidationError({"school": _("Only students, teachers and school staff belong to a school.")})
    if school is None:
        return leave_school(user, request=request)
    if not school.is_verified:
        raise ValidationError({"school": _("That school isn't verified yet.")})
    code_ok = bool(code) and normalise_code(code) == school.join_code and user.role != "school_admin"
    if code and not code_ok and user.role != "school_admin":
        raise ValidationError(
            {
                "school_code": _(
                    "That code doesn't match this school. Check it with your school, or leave it empty to ask for approval."
                )
            }
        )
    if user.school_id == school.pk and user.school_status == user.SchoolStatus.APPROVED:
        return user  # already an approved member: picking the same school again changes nothing
    fields = ["school", "school_status", "school_approved_at", "school_approved_by"]
    if user.school_id != school.pk:
        fields += _drop_school_teacher_approval(user)
    user.school = school
    if code_ok or approved_by is not None:
        _approve(user, approved_by)
    else:
        user.school_status = user.SchoolStatus.PENDING
        user.school_approved_at = None
        user.school_approved_by = None
    user.save(update_fields=fields)
    access.forget(user)
    if request is not None:
        audit.record(request, "choose_school", user, school=school.id, status=user.school_status, by_code=code_ok)
    return user


def _approve(user, approver):
    user.school_status = user.SchoolStatus.APPROVED
    user.school_approved_at = timezone.now()
    user.school_approved_by = approver


def _drop_school_teacher_approval(user):
    """A teacher approved by their school stops being approved when they leave it.
    Returns the fields to save."""
    if user.teacher_approved_by_school_id is None:
        return []
    user.teacher_approved = False
    user.teacher_approved_by_school = None
    return ["teacher_approved", "teacher_approved_by_school"]


def leave_school(user, request=None):
    old = user.school_id
    fields = ["school", "school_status", "school_approved_at", "school_approved_by", *_drop_school_teacher_approval(user)]
    user.school = None
    user.school_status = user.SchoolStatus.NONE
    user.school_approved_at = None
    user.school_approved_by = None
    user.save(update_fields=fields)
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
        raise PermissionDenied(_("Only this school's administrators can do that."))


def lock_for_decision(actor, school):
    """Inside a transaction: lock the school row, so decisions about its members happen one at a time,
    and check the actor's powers again from the database (another administrator may have removed them,
    or the school been suspended, while their request was on its way)."""
    school = type(school).objects.select_for_update().get(pk=school.pk)
    fresh = type(actor).objects.select_related("school").get(pk=actor.pk)
    require_manager(fresh, school)
    return school


def needs_teacher_confirmation(user):
    """A teacher the school could vouch for: not yet approved, and not stopped by the Iga team."""
    return user.role == "teacher" and not user.teacher_approved and not user.teacher_revoked


@transaction.atomic
def decide(actor, school, members, approve, request=None):
    """Approve or reject pending requests for `school`, and confirm approved members who are
    teachers (for example, teachers who joined with the code). Returns the users changed."""
    require_manager(actor, school)
    school = lock_for_decision(actor, school)
    # Decide on the rows as they are now (locked), not as they were when the request was read.
    members = list(type(actor).objects.select_for_update().filter(pk__in=[m.pk for m in members]).order_by("pk"))
    changed = []
    for user in members:
        if user.school_id != school.pk:
            continue
        confirm_teacher_only = approve and user.school_status == user.SchoolStatus.APPROVED and needs_teacher_confirmation(user)
        if user.school_status != user.SchoolStatus.PENDING and not confirm_teacher_only:
            continue
        if approve:
            fields = []
            if not confirm_teacher_only:
                _approve(user, actor)
                fields += ["school_status", "school_approved_at", "school_approved_by"]
            if needs_teacher_confirmation(user):
                # The school vouches for its own teachers, for as long as they stay members.
                user.teacher_approved = True
                user.teacher_approved_by_school = school
                fields += ["teacher_approved", "teacher_approved_by_school"]
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


@transaction.atomic
def remove(actor, school, user, request=None):
    require_manager(actor, school)
    school = lock_for_decision(actor, school)
    user = type(user).objects.select_for_update().get(pk=user.pk)
    if user.school_id != school.pk:
        raise ValidationError({"user": _("That person isn't a member of this school.")})
    if user.pk == actor.pk:
        raise ValidationError({"user": _("You can't remove yourself.")})
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
