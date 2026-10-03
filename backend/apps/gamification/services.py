"""XP, streaks and badges. Call these from views after a learning action succeeds."""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import Badge, UserBadge, XPEvent

XP_LESSON = 10
XP_FIRST_SIMULATION_VIEW = 5
XP_QUIZ_BASE = 5
XP_PERFECT_BONUS = 10
XP_JOIN_GROUP = 5

BADGES = {
    "first-lesson": ("First Steps", "Completed your first lesson", "👣"),
    "bookworm": ("Bookworm", "Completed 10 lessons", "📚"),
    "quiz-whiz": ("Quiz Whiz", "Scored 100% on a quiz", "🎯"),
    "exam-ready": ("Exam Ready", "Finished a past national exam paper", "📝"),
    "lab-explorer": ("Lab Explorer", "Explored 5 different simulations", "🔬"),
    "team-player": ("Team Player", "Joined a study group", "🤝"),
    "streak-3": ("On a Roll", "Learned 3 days in a row", "🔥"),
    "streak-7": ("Unstoppable", "Learned 7 days in a row", "⚡"),
}


def ensure_badges():
    for code, (name, description, icon) in BADGES.items():
        Badge.objects.update_or_create(code=code, defaults={"name": name, "description": description, "icon": icon})


def award_badge(user, code):
    """Award a badge once. Returns True if newly awarded."""
    if code not in BADGES:
        raise ValueError(f"Unknown badge {code}")
    name, description, icon = BADGES[code]
    badge, _ = Badge.objects.get_or_create(code=code, defaults={"name": name, "description": description, "icon": icon})
    _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
    return created


def award_xp(user, amount, reason, reference=""):
    """Add XP. With a `reference`, the same action is never rewarded twice. Returns XP actually awarded."""
    if amount <= 0:
        return 0
    try:
        with transaction.atomic():
            XPEvent.objects.create(user=user, amount=amount, reason=reason, reference=reference)
            type(user).objects.filter(pk=user.pk).update(xp=F("xp") + amount)
    except IntegrityError:
        return 0
    user.refresh_from_db(fields=["xp"])
    touch_activity(user)
    return amount


def touch_activity(user, today=None):
    """Update the daily learning streak."""
    today = today or timezone.localdate()
    if user.last_active_date == today:
        return
    if user.last_active_date == today - timedelta(days=1):
        user.streak_days += 1
    else:
        user.streak_days = 1
    user.last_active_date = today
    user.save(update_fields=["streak_days", "last_active_date"])
    if user.streak_days >= 3:
        award_badge(user, "streak-3")
    if user.streak_days >= 7:
        award_badge(user, "streak-7")


def quiz_xp(percentage):
    """XP for finishing a quiz the first time: a base amount plus 1 per 10%."""
    if percentage is None:
        return XP_QUIZ_BASE
    return XP_QUIZ_BASE + int(percentage // 10)


def on_lesson_completed(user, lesson):
    gained = award_xp(user, XP_LESSON, "lesson", f"lesson:{lesson.pk}")
    count = user.lesson_progress.count()
    if count >= 1:
        award_badge(user, "first-lesson")
    if count >= 10:
        award_badge(user, "bookworm")
    return gained


def on_simulation_viewed(user, simulation):
    gained = award_xp(user, XP_FIRST_SIMULATION_VIEW, "simulation", f"sim:{simulation.pk}")
    if user.simulation_views.values("simulation").distinct().count() >= 5:
        award_badge(user, "lab-explorer")
    return gained


def _attempt_was_blank(attempt):
    return not any(
        a.text_answer.strip() or a.numeric_answer is not None or a.selected_choices.exists() for a in attempt.answers.all()
    )


def on_attempt_marked(attempt):
    """Quiz XP is earned once per quiz (retakes are for learning, not farming), plus a
    one-off bonus the first time the student gets everything right."""
    user = attempt.user
    if _attempt_was_blank(attempt):
        return 0
    pct = attempt.percentage
    gained = award_xp(user, quiz_xp(pct), "quiz", f"quiz:{attempt.quiz_id}")
    if pct is not None and pct >= 100:
        gained += award_xp(user, XP_PERFECT_BONUS, "quiz-perfect", f"quiz-perfect:{attempt.quiz_id}")
        award_badge(user, "quiz-whiz")
    if attempt.quiz.kind == "past_paper":
        award_badge(user, "exam-ready")
    return gained


def on_group_joined(user, group):
    award_badge(user, "team-player")
    return award_xp(user, XP_JOIN_GROUP, "group", f"group:{group.pk}")
