"""Personal-data export and erase for Teaching Packs (the shared account-data convention)."""

from .models import TeachingPack


def export_for(user):
    return {
        "teaching_packs": [
            {
                "unit": (pack.document.get("unit") or {}).get("label", ""),
                "lesson": (pack.document.get("lesson") or {}).get("title", ""),
                "created_at": pack.created_at.isoformat(),
                "language": pack.language,
                "plan_edits": pack.plan_edits,
            }
            for pack in TeachingPack.objects.filter(created_by=user)
        ]
    }


def erase_for(user):
    TeachingPack.objects.filter(created_by=user).delete()
