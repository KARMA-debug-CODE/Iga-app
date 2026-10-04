"""Who may open premium content.

Premium content is unlocked by membership of a school whose subscription is active. Everything
else on the platform (free lessons and quizzes, labs, playgrounds, classes, groups) stays open
to every signed-in user. Keep every check going through `content_access` so there is one rule.
"""

from dataclasses import dataclass

from rest_framework.exceptions import PermissionDenied

ELIGIBLE_ROLES = {"student", "teacher", "school_admin"}


@dataclass(frozen=True)
class Access:
    premium: bool
    # Why premium is unavailable: no_school | pending_approval | rejected | school_not_verified |
    # not_subscribed | expired | not_eligible | "" when premium.
    reason: str = ""


class SubscriptionRequired(PermissionDenied):
    default_detail = "This is part of the full Iga library. Ask your school to subscribe to unlock it."
    default_code = "subscription_required"


def content_access(user):
    """Cached on the user object for the rest of the request."""
    cached = getattr(user, "_content_access", None)
    if cached is not None:
        return cached
    result = _compute(user)
    if user is not None and getattr(user, "is_authenticated", False):
        user._content_access = result
    return result


def _compute(user):
    if user is None or not user.is_authenticated:
        return Access(False, "no_school")
    if user.is_platform_admin:
        return Access(True)
    if user.role not in ELIGIBLE_ROLES:
        return Access(False, "not_eligible")
    if not user.school_id:
        return Access(False, "no_school")
    if user.school_status == "pending":
        return Access(False, "pending_approval")
    if user.school_status != "approved":
        return Access(False, "rejected")
    school = user.school
    if not school.is_verified:
        return Access(False, "school_not_verified")
    if school.paid_until is None:
        return Access(False, "not_subscribed")
    if not school.subscription_active():
        return Access(False, "expired")
    return Access(True)


def has_premium(user):
    return content_access(user).premium


def can_open(user, item):
    """item is a Lesson, Quiz (anything with `is_free`) - free items are open to everyone."""
    return bool(getattr(item, "is_free", False)) or has_premium(user)


def require(user, item=None):
    """Raise 403 subscription_required unless the user may open `item` (or premium content if None)."""
    allowed = can_open(user, item) if item is not None else has_premium(user)
    if not allowed:
        raise SubscriptionRequired()


def forget(user):
    """Drop the cached result (after a payment or a membership change in the same request)."""
    if hasattr(user, "_content_access"):
        del user._content_access
