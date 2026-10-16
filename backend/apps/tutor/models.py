from django.conf import settings
from django.db import models


class TutorExchange(models.Model):
    """One question to Santa and its answer, kept for safeguarding review."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_exchanges")
    lesson = models.ForeignKey("curriculum.Lesson", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    attempt = models.ForeignKey("assessments.Attempt", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    question = models.ForeignKey("assessments.Question", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    # The subject chosen on the Santa page (empty for questions asked from a lesson or a quiz).
    subject = models.ForeignKey("curriculum.Subject", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    message = models.TextField()
    reply = models.TextField(blank=True)
    # The model's name on Santa's model server, or "lessons" for an answer made of lesson passages.
    model = models.CharField(max_length=64, blank=True)
    stop_reason = models.CharField(max_length=32, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    # What the prompt-injection defences noticed (apps/tutor/guard.py), comma-separated: "injection" (the
    # message tried to instruct the model), "forged_history" (earlier answers Santa never gave were sent),
    # "prompt_leak" (the answer repeated Santa's instructions and was replaced). Empty for most questions.
    flags = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} · {self.created_at:%Y-%m-%d %H:%M}"


class SantaUsage(models.Model):
    """How much one student used Santa's model on one day: what the allowances count (apps/tutor/usage.py).

    `school` is the student's school when they last asked that day, for the per-school budget."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="santa_usage")
    school = models.ForeignKey("schools.School", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    day = models.DateField()
    # Questions the model answered, and the tokens they took (as the model server reported them, or estimated
    # from the text when an answer was stopped before the server said).
    questions = models.PositiveIntegerField(default=0)
    input_tokens = models.PositiveBigIntegerField(default=0)
    output_tokens = models.PositiveBigIntegerField(default=0)
    # Questions answered from the lessons because an allowance was used up.
    limited = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-day"]
        constraints = [models.UniqueConstraint(fields=["user", "day"], name="santa_usage_one_row_per_day")]
        indexes = [models.Index(fields=["school", "day"]), models.Index(fields=["day"])]

    def __str__(self):
        return f"{self.user} · {self.day}"
