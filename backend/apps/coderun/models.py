from django.conf import settings
from django.db import models


class CodeRunUsage(models.Model):
    """How much one user used the code runner on one day: what the daily limits count (services.py)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="code_run_usage")
    day = models.DateField()
    runs = models.PositiveIntegerField(default=0)  # programs the runner started
    cpu_ms = models.PositiveBigIntegerField(default=0)  # CPU time compiling and running them, as the runner measured it
    limited = models.PositiveIntegerField(default=0)  # runs and answers refused because a daily limit was reached

    class Meta:
        ordering = ["-day"]
        constraints = [models.UniqueConstraint(fields=["user", "day"], name="code_run_usage_one_row_per_day")]
        indexes = [models.Index(fields=["day"])]

    def __str__(self):
        return f"{self.user} · {self.day}"
