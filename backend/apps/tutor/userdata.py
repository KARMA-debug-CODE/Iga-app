"""Santa's part of "Download my data" and "Delete my account" (apps/accounts/privacy.py)."""

from apps.core.exporting import iso

from .models import SantaUsage, TutorExchange


def export_for(user):
    exchanges = TutorExchange.objects.filter(user=user).select_related("lesson", "subject").order_by("created_at")
    return {
        "questions": [
            {
                "asked_at": iso(e.created_at),
                "question": e.message,
                "answer": e.reply,
                "lesson": e.lesson.slug if e.lesson_id else None,
                "subject": e.subject.code if e.subject_id else None,
                "answered_by": e.model,
            }
            for e in exchanges
        ],
        "daily_usage": [
            {"day": iso(u.day), "questions": u.questions, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens}
            for u in SantaUsage.objects.filter(user=user).order_by("day")
        ],
    }


def erase_for(user):
    TutorExchange.objects.filter(user=user).delete()
    SantaUsage.objects.filter(user=user).delete()
