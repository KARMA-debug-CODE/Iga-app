"""The curriculum app's part of "Download my data" and "Delete my account" (apps/accounts/privacy.py)."""

from apps.core.exporting import iso

from .models import Lesson, LessonProgress, Resource


def export_for(user):
    return {
        "lessons_completed": [
            {"lesson": p.lesson.slug, "title": p.lesson.title, "completed_at": iso(p.completed_at)}
            for p in LessonProgress.objects.filter(user=user).select_related("lesson").order_by("completed_at")
        ],
        # Teaching material this user wrote or uploaded (it stays on Iga after an erasure, without their name).
        "lessons_written": [
            {"lesson": lesson.slug, "title": lesson.title, "status": lesson.status, "created_at": iso(lesson.created_at)}
            for lesson in Lesson.objects.filter(author=user).order_by("created_at")
        ],
        "resources_uploaded": [
            {"title": r.title, "kind": r.kind, "status": r.status, "created_at": iso(r.created_at)}
            for r in Resource.objects.filter(uploaded_by=user).order_by("created_at")
        ],
    }


def erase_for(user):
    # The learner's own progress goes. Lessons and resources a teacher wrote are teaching material that classes
    # use: they stay, pointing at the emptied account ("Deleted account").
    LessonProgress.objects.filter(user=user).delete()
