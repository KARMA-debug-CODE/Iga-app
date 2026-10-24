"""The code runner's part of "Download my data" and "Delete my account" (apps/accounts/privacy.py). The code
itself is never stored: only how much the runner was used each day."""

from apps.core.exporting import iso

from .models import CodeRunUsage


def export_for(user):
    return {
        "daily_usage": [
            {"day": iso(u.day), "runs": u.runs, "cpu_ms": u.cpu_ms, "refused": u.limited}
            for u in CodeRunUsage.objects.filter(user=user).order_by("day")
        ]
    }


def erase_for(user):
    CodeRunUsage.objects.filter(user=user).delete()
