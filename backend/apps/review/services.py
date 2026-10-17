"""The spaced-repetition (Leitner) deck: which questions are due, and what a review answer does.

Correctness is always decided on the server (apps.assessments.services.grade_response), exactly like a
normal attempt; the client never sends whether its answer was right. A correct review gives a small,
capped amount of XP (REVIEW_XP, up to REVIEW_XP_DAILY_CAP a day) so the deck can't be farmed.
"""

from datetime import timedelta
from uuid import uuid4

from django.db import models, transaction
from django.utils import timezone

from apps.assessments.models import Question
from apps.assessments.services import grade_response, library_questions_q
from apps.gamification import services as gamification
from apps.gamification.models import XPEvent
from apps.schools.access import has_premium

from .models import ReviewItem

# How long each Leitner box waits before an item is due again (days). Box 0..4.
REVIEW_INTERVALS = (1, 3, 7, 14, 30)
LAST_BOX = len(REVIEW_INTERVALS) - 1

REVIEW_XP = 1  # a correct review is worth a little, not as much as a quiz
REVIEW_XP_DAILY_CAP = 5  # ...and only a handful a day, so the deck can't be farmed for XP


def next_schedule(box, correct):
    """Return (new_box, days_until_due); (None, None) means the item graduates out of the deck."""
    if correct:
        if box >= LAST_BOX:
            return None, None
        new_box = box + 1
        return new_box, REVIEW_INTERVALS[new_box]
    return 0, REVIEW_INTERVALS[0]


# --- The deck ----------------------------------------------------------------


def visible_items(user):
    """A user's active deck, minus library questions they can't currently open (the paywall still holds)."""
    qs = ReviewItem.objects.filter(user=user, retired_at__isnull=True).select_related("question", "question__subject")
    if not has_premium(user):
        qs = qs.exclude(library_questions_q("question__"))
    return qs


def due_items(user, today=None):
    today = today or timezone.localdate()
    return visible_items(user).filter(due_on__lte=today)


def due_count(user, today=None):
    return due_items(user, today).count()


def deck_count(user):
    return visible_items(user).count()


# --- Filling the deck --------------------------------------------------------


def add_question(user, question, today=None):
    """Put a question in the user's deck (box 0, due today) if it isn't already active there. A question
    that was retired and is wrong again starts over at box 0."""
    if question.needs_manual_marking:
        return  # essays and open short answers can't be auto-marked, so they can't be self-revised
    today = today or timezone.localdate()
    item, created = ReviewItem.objects.get_or_create(user=user, question=question, defaults={"box": 0, "due_on": today})
    if not created and item.retired_at is not None:
        item.box = 0
        item.due_on = today
        item.retired_at = None
        item.save(update_fields=["box", "due_on", "retired_at"])


def add_wrong_answers(attempt):
    """Called after an attempt is checked or submitted: add every auto-marked question the student got
    wrong (is_correct is False) to their review deck. Correct answers and manual ones are left out."""
    answers = [a for a in attempt.answers.all() if a.is_correct is False]
    if not answers:
        return
    questions = Question.objects.in_bulk([a.question_id for a in answers])
    user = attempt.user
    today = timezone.localdate()
    for answer in answers:
        question = questions.get(answer.question_id)
        if question is not None:
            add_question(user, question, today)


# --- Reviewing ---------------------------------------------------------------


def award_review_xp(user):
    """A little XP for a correct review, capped per day so the deck can't be used to farm XP."""
    today = timezone.localdate()
    earned = (
        XPEvent.objects.filter(user=user, reason="review", created_at__date=today).aggregate(total=models.Sum("amount"))["total"]
        or 0
    )
    if earned >= REVIEW_XP_DAILY_CAP:
        return 0
    return gamification.award_xp(user, REVIEW_XP, "review", reference=f"review:{user.id}:{uuid4().hex}")


@transaction.atomic
def grade_item(item, *, choice_ids=(), text="", numeric=None):
    """Grade one due review item on the server and move it along the Leitner schedule.

    Returns (is_correct, xp_gained). The item is re-read under a row lock so two taps can't advance it
    twice."""
    item = ReviewItem.objects.select_for_update().get(pk=item.pk)
    is_correct, _marks = grade_response(item.question, choice_ids=choice_ids, text=text, numeric=numeric)
    is_correct = bool(is_correct)
    item.times_seen += 1
    if is_correct:
        item.times_correct += 1
    item.last_reviewed_at = timezone.now()
    new_box, days = next_schedule(item.box, is_correct)
    if new_box is None:
        item.retired_at = timezone.now()
    else:
        item.box = new_box
        item.due_on = timezone.localdate() + timedelta(days=days)
    item.save()
    xp = award_review_xp(item.user) if is_correct else 0
    return is_correct, xp
