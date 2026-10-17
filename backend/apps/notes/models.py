from django.conf import settings
from django.db import models


class LessonBookmark(models.Model):
    """A lesson a student has saved to come back to. Owned by the student; nobody else sees it."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_bookmarks")
    lesson = models.ForeignKey("curriculum.Lesson", on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "lesson"], name="unique_lesson_bookmark")]

    def __str__(self):
        return f"{self.user_id} · {self.lesson_id}"


class LessonNote(models.Model):
    """A student's private note on one lesson. Plain text, cleaned and length-limited, shown only to its
    author (there is no sharing: every query is scoped to the owner)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_notes")
    lesson = models.ForeignKey("curriculum.Lesson", on_delete=models.CASCADE, related_name="notes")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["user", "lesson"], name="unique_lesson_note")]

    def __str__(self):
        return f"{self.user_id} · {self.lesson_id}"
