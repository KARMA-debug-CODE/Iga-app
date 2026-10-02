from django.conf import settings
from django.db import models


class TutorExchange(models.Model):
    """One question to the AI tutor and its reply, kept for safeguarding review and cost tracking."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_exchanges")
    lesson = models.ForeignKey("curriculum.Lesson", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    attempt = models.ForeignKey("assessments.Attempt", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    question = models.ForeignKey("assessments.Question", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    message = models.TextField()
    reply = models.TextField(blank=True)
    model = models.CharField(max_length=64, blank=True)
    stop_reason = models.CharField(max_length=32, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} · {self.created_at:%Y-%m-%d %H:%M}"
