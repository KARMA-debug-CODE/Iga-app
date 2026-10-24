"""The audit log's part of "Download my data" and "Delete my account" (apps/accounts/privacy.py).

The audit log is kept for accountability and security for AUDIT_LOG_RETENTION_DAYS. After an erasure its
entries about the account stay, pointing at the emptied row, without the IP addresses and usernames they
recorded."""

from django.db.models import Q

from apps.core.exporting import iso

from .models import AuditLog

# The most recent entries in a download (a busy account can have many sign-ins).
EXPORT_LIMIT = 1000
PERSONAL_DETAILS = ("username", "email", "identifier", "name")


def _about(user):
    return Q(actor=user) | Q(target_type="accounts.user", target_id=str(user.pk))


def export_for(user):
    entries = AuditLog.objects.filter(actor=user).order_by("-created_at")[:EXPORT_LIMIT]
    return {
        "activity_log": [
            {"action": e.action, "at": iso(e.created_at), "ip_address": e.ip_address, "about": e.target_type} for e in entries
        ]
    }


def erase_for(user):
    for entry in AuditLog.objects.filter(_about(user)).only("id", "details", "ip_address").iterator():
        details = {k: v for k, v in (entry.details or {}).items() if k not in PERSONAL_DETAILS}
        if details != entry.details or entry.ip_address is not None:
            AuditLog.objects.filter(pk=entry.pk).update(details=details, ip_address=None)
