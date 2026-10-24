from django.conf import settings
from django.db import models


class StudyPlan(models.Model):
    """A student's weekly study goal. One per user, created the first time they set a goal."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_plan")
    weekly_goal_lessons = models.PositiveSmallIntegerField(default=5, help_text="Lessons to finish each week")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} · {self.weekly_goal_lessons}/week"


class ExamDate(models.Model):
    """An exam the student is working towards (for example the national exam), for the dashboard countdown."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_dates")
    title = models.CharField(max_length=120)
    date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "id"]

    def __str__(self):
        return f"{self.title} ({self.date})"
