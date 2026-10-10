from django.conf import settings
from django.db import models


class Badge(models.Model):
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=200)
    icon = models.CharField(max_length=32, default="award", help_text="Name of a line icon (see Icon.jsx)")

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="awards")
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-awarded_at"]
        constraints = [models.UniqueConstraint(fields=["user", "badge"], name="unique_user_badge")]


class XPEvent(models.Model):
    """Ledger of every XP award; weekly leaderboards are sums over this table."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xp_events")
    amount = models.IntegerField()
    reason = models.CharField(max_length=40)
    # Stops the same action being rewarded twice (e.g. "lesson:42", "attempt:7").
    reference = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "reference"], condition=~models.Q(reference=""), name="unique_xp_reference")
        ]
