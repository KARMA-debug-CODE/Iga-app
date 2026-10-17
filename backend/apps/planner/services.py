"""The study planner: the weekly goal, the exam countdown and the suggested next steps on the dashboard.

Everything here reads only the signed-in student's own data. Suggestions point at unfinished lessons in
the units where the student's quiz scores are weakest, and at the reviews that are due today."""

from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.assessments.models import Attempt
from apps.core.constants import ContentStatus
from apps.curriculum.models import LessonProgress
from apps.review import services as review_services
from apps.schools.access import has_premium

from .models import ExamDate, StudyPlan

DEFAULT_WEEKLY_GOAL = 5
MAX_WEEKLY_GOAL = 50
MAX_EXAM_DATES = 10
MAX_SUGGESTIONS = 4


def get_plan(user):
    return StudyPlan.objects.filter(user=user).first()


def weekly_goal(user):
    plan = get_plan(user)
    return plan.weekly_goal_lessons if plan else DEFAULT_WEEKLY_GOAL


def week_start(today=None):
    """The Monday of this week (Kigali time)."""
    today = today or timezone.localdate()
    return today - timedelta(days=today.weekday())


def lessons_this_week(user, today=None):
    start = week_start(today)
    return LessonProgress.objects.filter(user=user, completed_at__date__gte=start).count()


def _weak_unit_lessons(user, lang, done_ids, limit):
    """One unfinished, openable lesson from each of the student's weakest-scoring units."""
    from apps.curriculum.views import visible_lessons

    rows = (
        Attempt.objects.filter(user=user, quiz__unit__isnull=False, max_score__gt=0)
        .exclude(status=Attempt.Status.IN_PROGRESS)
        .values("quiz__unit")
        .annotate(score=Sum("score"), total=Sum("max_score"))
    )
    ranked = sorted(rows, key=lambda r: float(r["score"] or 0) / float(r["total"] or 1))
    premium = has_premium(user)
    out = []
    for row in ranked:
        lessons = (
            visible_lessons(user)
            .filter(unit_id=row["quiz__unit"], status=ContentStatus.PUBLISHED)
            .exclude(id__in=done_ids)
            .select_related("unit", "unit__subject")
            .order_by("order")
        )
        if not premium:
            lessons = lessons.filter(is_free=True)
        lesson = lessons.first()
        if lesson is None:
            continue
        translation = lesson.translations.filter(language=lang).first() if lang != "en" else None
        out.append(
            {
                "type": "lesson",
                "slug": lesson.slug,
                "title": translation.title if translation else lesson.title,
                "subject": lesson.unit.subject.localized_name(lang),
                "icon": lesson.unit.subject.icon,
                "unit_number": lesson.unit.number,
            }
        )
        if len(out) >= limit:
            break
    return out


def suggestions(user, lang="en"):
    """Up to MAX_SUGGESTIONS next steps: due reviews first, then weak-unit lessons."""
    out = []
    due = review_services.due_count(user)
    if due:
        out.append({"type": "review", "count": due})
    done_ids = set(LessonProgress.objects.filter(user=user).values_list("lesson_id", flat=True))
    out.extend(_weak_unit_lessons(user, lang, done_ids, MAX_SUGGESTIONS - len(out)))
    return out


def dashboard_summary(user, lang="en"):
    """The planner block on the student dashboard: goal, this week's progress, countdown, next steps."""
    today = timezone.localdate()
    next_exam = ExamDate.objects.filter(user=user, date__gte=today).order_by("date").first()
    return {
        "has_plan": get_plan(user) is not None,
        "weekly_goal": weekly_goal(user),
        "lessons_this_week": lessons_this_week(user, today),
        "next_exam": (
            {"title": next_exam.title, "date": next_exam.date.isoformat(), "days_left": (next_exam.date - today).days}
            if next_exam
            else None
        ),
        "suggestions": suggestions(user, lang),
    }
