"""The gamification app's part of "Download my data" and "Delete my account" (apps/accounts/privacy.py)."""

from apps.core.exporting import iso

from .models import UserBadge, XPEvent


def export_for(user):
    return {
        "xp_events": [
            {"amount": e.amount, "reason": e.reason, "reference": e.reference, "created_at": iso(e.created_at)}
            for e in XPEvent.objects.filter(user=user).order_by("created_at")
        ],
        "badges": [
            {"badge": b.badge.code, "name": b.badge.name, "awarded_at": iso(b.awarded_at)}
            for b in UserBadge.objects.filter(user=user).select_related("badge").order_by("awarded_at")
        ],
    }


def erase_for(user):
    # Leaderboards are sums over the XP ledger, so the account leaves them too.
    XPEvent.objects.filter(user=user).delete()
    UserBadge.objects.filter(user=user).delete()
