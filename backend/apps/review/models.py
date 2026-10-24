from django.conf import settings
from django.db import models


class ReviewItem(models.Model):
    """One question a student got wrong, waiting to be revised on a Leitner (spaced-repetition) schedule.

    Each item sits in a box (0-4). The boxes wait 1, 3, 7, 14 and 30 days (REVIEW_INTERVALS). A correct
    answer in a review session moves the item up a box and pushes its due date out; a wrong answer sends
    it back to box 0. Once a correct answer leaves the last box, the item is retired (retired_at is set)
    and no longer revised. The row owner is the student: nobody else ever reads or writes it.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_items")
    question = models.ForeignKey("assessments.Question", on_delete=models.CASCADE, related_name="review_items")
    box = models.PositiveSmallIntegerField(default=0, help_text="0-based Leitner box")
    due_on = models.DateField(db_index=True, help_text="The next day this item is due for review (Kigali time)")
    times_seen = models.PositiveSmallIntegerField(default=0)
    times_correct = models.PositiveSmallIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True, help_text="Set once the item has graduated out of the deck")

    class Meta:
        ordering = ["due_on", "id"]
        constraints = [models.UniqueConstraint(fields=["user", "question"], name="unique_review_item")]
        indexes = [models.Index(fields=["user", "retired_at", "due_on"])]

    def __str__(self):
        return f"{self.user_id} · Q{self.question_id} · box {self.box}"
