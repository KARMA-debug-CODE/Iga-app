"""The study planner: weekly goal, exam countdown and suggested next steps."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.assessments.models import Attempt
from apps.curriculum.models import Lesson, LessonProgress
from apps.planner import services, userdata
from apps.planner.models import ExamDate, StudyPlan
from apps.review.models import ReviewItem

from .conftest import add_mcq, make_quiz, make_user

pytestmark = pytest.mark.django_db


def test_setting_and_reading_the_weekly_goal(client_for):
    student = make_user("planner")
    client = client_for(student)
    # No plan yet: the default goal is reported.
    data = client.get("/api/planner/").data
    assert data["has_plan"] is False and data["weekly_goal_lessons"] == services.DEFAULT_WEEKLY_GOAL
    client.put("/api/planner/", {"weekly_goal_lessons": 3}, format="json")
    data = client.get("/api/planner/").data
    assert data["has_plan"] is True and data["weekly_goal_lessons"] == 3
    assert StudyPlan.objects.filter(user=student).count() == 1


def test_the_weekly_goal_is_bounded(client_for):
    client = client_for(make_user("bounds"))
    assert client.put("/api/planner/", {"weekly_goal_lessons": 0}, format="json").status_code == 400
    assert client.put("/api/planner/", {"weekly_goal_lessons": 999}, format="json").status_code == 400


def test_adding_listing_and_removing_exam_dates(client_for):
    student = make_user("exams")
    client = client_for(student)
    future = (timezone.localdate() + timedelta(days=60)).isoformat()
    created = client.post("/api/planner/exams/", {"title": "National exam", "date": future}, format="json")
    assert created.status_code == 201
    exam_id = created.data["id"]
    listed = client.get("/api/planner/exams/").data
    assert any(e["title"] == "National exam" for e in (listed if isinstance(listed, list) else listed["results"]))
    assert client.delete(f"/api/planner/exams/{exam_id}/").status_code == 204
    assert ExamDate.objects.filter(user=student).count() == 0


def test_a_past_exam_date_is_refused(client_for):
    client = client_for(make_user("past"))
    past = (timezone.localdate() - timedelta(days=1)).isoformat()
    assert client.post("/api/planner/exams/", {"title": "Gone", "date": past}, format="json").status_code == 400


def test_exam_dates_are_capped(client_for):
    student = make_user("many-exams")
    client = client_for(student)
    date = (timezone.localdate() + timedelta(days=30)).isoformat()
    for i in range(services.MAX_EXAM_DATES):
        assert client.post("/api/planner/exams/", {"title": f"Exam {i}", "date": date}, format="json").status_code == 201
    assert client.post("/api/planner/exams/", {"title": "One too many", "date": date}, format="json").status_code == 400


def test_dashboard_summary_counts_this_weeks_lessons_and_the_countdown(subject, unit):
    student = make_user("summary")
    lesson = Lesson.objects.create(unit=unit, slug="done", title="Done", body="x", status="published", is_free=True)
    LessonProgress.objects.create(user=student, lesson=lesson)
    ExamDate.objects.create(user=student, title="Mock", date=timezone.localdate() + timedelta(days=10))
    summary = services.dashboard_summary(student)
    assert summary["lessons_this_week"] == 1
    assert summary["next_exam"]["days_left"] == 10 and summary["next_exam"]["title"] == "Mock"


def test_suggestions_point_at_due_reviews_and_weak_unit_lessons(subject, unit):
    student = make_user("weak")
    # A finished quiz in this unit with a poor score makes the unit "weak".
    question = add_mcq(subject, unit)
    quiz = make_quiz(subject, unit, [question], is_free=True)
    Attempt.objects.create(
        user=student, quiz=quiz, status=Attempt.Status.MARKED, score=0, max_score=1, submitted_at=timezone.now()
    )
    # An unfinished, openable lesson in that weak unit, and a due review.
    Lesson.objects.create(unit=unit, slug="weak-lesson", title="Weak topic", body="x", status="published", is_free=True)
    ReviewItem.objects.create(user=student, question=question, due_on=timezone.localdate())

    kinds = {s["type"] for s in services.suggestions(student)}
    assert "review" in kinds and "lesson" in kinds
    lesson_suggestion = next(s for s in services.suggestions(student) if s["type"] == "lesson")
    assert lesson_suggestion["slug"] == "weak-lesson"


def test_export_and_erase_cover_the_planner():
    student = make_user("export-plan")
    StudyPlan.objects.create(user=student, weekly_goal_lessons=6)
    ExamDate.objects.create(user=student, title="Finals", date=timezone.localdate() + timedelta(days=20))
    exported = userdata.export_for(student)
    assert exported["study_plan"]["weekly_goal_lessons"] == 6 and len(exported["exam_dates"]) == 1
    userdata.erase_for(student)
    assert not StudyPlan.objects.filter(user=student).exists()
    assert not ExamDate.objects.filter(user=student).exists()
