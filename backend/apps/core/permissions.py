"""Who may do what: every role check the API makes, in one place.

Roles (User.role): student, teacher (acts as one once approved), parent, school_admin (powers only while
an approved member of a verified school), admin (the Iga team; superusers count as admins).

Views combine these classes; DRF requires all of them. Privileged operations add RecentAuthentication:

| Operation                                                       | Who                | Step-up |
|-----------------------------------------------------------------|--------------------|---------|
| Everything under /api/admin/ (users, roles, teacher approval,   | IsPlatformAdmin    | yes     |
| content review, moderation, schools, payments, audit, stats)    |                    |         |
| Approve or remove school members, confirm teachers, new code,   | IsSchoolAdmin      | yes     |
| start a subscription payment                                    |                    |         |
| Reset a student's password                                      | IsTeacher (class)  | yes     |

"Step-up" means the user signed in, or confirmed their password (and 2FA code when it is on) at
POST /api/auth/step-up/, within STEP_UP_MAX_AGE_SECONDS. Each of these operations is audit-logged.
Object-level rules (whose class, whose school, whose child) live in each view's queryset.
"""

import time

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

STEP_UP_CODE = "step_up_required"
# Tolerated difference between this server's clock and the one that signed the token (seconds).
CLOCK_SKEW_SECONDS = 60


def _user(request):
    user = getattr(request, "user", None)
    return user if user is not None and user.is_authenticated else None


class IsStudent(BasePermission):
    message = gettext_lazy("Only students can do this.")

    def has_permission(self, request, view):
        user = _user(request)
        return bool(user and user.is_student)


class IsParent(BasePermission):
    message = gettext_lazy("Only parent or guardian accounts can do this.")

    def has_permission(self, request, view):
        user = _user(request)
        return bool(user and user.is_parent)


class NotParent(BasePermission):
    """Keeps parent accounts out of student spaces such as study-group chats."""

    message = gettext_lazy("Study groups are for students and teachers.")

    def has_permission(self, request, view):
        user = _user(request)
        return bool(user and not user.is_parent)


class IsTeacher(BasePermission):
    message = gettext_lazy("Only approved teachers can do this.")

    def has_permission(self, request, view):
        user = _user(request)
        return bool(user and user.can_teach)


class IsPlatformAdmin(BasePermission):
    message = gettext_lazy("Only administrators can do this.")

    def has_permission(self, request, view):
        user = _user(request)
        return bool(user and user.is_platform_admin)


class IsSchoolAdmin(BasePermission):
    message = gettext_lazy("Only approved school administrators can do this.")

    def has_permission(self, request, view):
        user = _user(request)
        return bool(user and user.managed_school is not None)


class IsTeacherOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return _user(request) is not None
        return IsTeacher().has_permission(request, view)


def authenticated_at(request):
    """When this session's user last proved who they are (signed in or stepped up), as a Unix time, or None.

    The time is the "auth_time" claim of the access token: set by the login, registration and step-up
    endpoints, and carried unchanged through refreshes (so it ages; a refresh never renews it)."""
    token = getattr(request, "auth", None)
    getter = getattr(token, "get", None)
    if getter is None:
        return None
    try:
        value = getter("auth_time")
    except (KeyError, TypeError):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def recently_authenticated(request):
    value = authenticated_at(request)
    if value is None:
        return False
    age = time.time() - value
    return -CLOCK_SKEW_SECONDS <= age <= settings.STEP_UP_MAX_AGE_SECONDS


class RecentAuthentication(BasePermission):
    """The user proved who they are a few minutes ago. Put it after the role check, so someone without the
    role is told so instead of being asked for their password."""

    def has_permission(self, request, view):
        if _user(request) is None:
            return False
        if not recently_authenticated(request):
            raise PermissionDenied(
                {"detail": _("For your security, enter your password again to continue."), "code": STEP_UP_CODE}
            )
        return True
