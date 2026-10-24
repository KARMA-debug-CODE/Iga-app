"""Personal-data export and erase for bookmarks and private notes (the shared account-data convention)."""

from .models import LessonBookmark, LessonNote


def export_for(user):
    return {
        "bookmarks": [
            {"lesson": bookmark.lesson.slug, "lesson_title": bookmark.lesson.title, "created_at": bookmark.created_at.isoformat()}
            for bookmark in LessonBookmark.objects.filter(user=user).select_related("lesson")
        ],
        "lesson_notes": [
            {
                "lesson": note.lesson.slug,
                "lesson_title": note.lesson.title,
                "body": note.body,
                "updated_at": note.updated_at.isoformat(),
            }
            for note in LessonNote.objects.filter(user=user).select_related("lesson")
        ],
    }


def erase_for(user):
    LessonNote.objects.filter(user=user).delete()
    LessonBookmark.objects.filter(user=user).delete()
