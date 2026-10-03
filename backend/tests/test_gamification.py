from datetime import date, timedelta

import pytest

from apps.core.views import level_from_xp
from apps.gamification import services
from apps.gamification.models import XPEvent

pytestmark = pytest.mark.django_db


def test_xp_with_reference_is_awarded_once(student):
    assert services.award_xp(student, 10, "lesson", "lesson:1") == 10
    assert services.award_xp(student, 10, "lesson", "lesson:1") == 0
    assert services.award_xp(student, 5, "bonus") == 5
    assert services.award_xp(student, 5, "bonus") == 5  # no reference → always awarded
    student.refresh_from_db()
    assert student.xp == 20


def test_streaks(student):
    day = date(2026, 3, 1)
    for offset in range(3):
        services.touch_activity(student, day + timedelta(days=offset))
    assert student.streak_days == 3
    assert student.badges.filter(badge__code="streak-3").exists()
    services.touch_activity(student, day + timedelta(days=5))
    assert student.streak_days == 1


def test_same_day_activity_does_not_extend_streak(student):
    services.touch_activity(student, date(2026, 3, 1))
    services.touch_activity(student, date(2026, 3, 1))
    assert student.streak_days == 1


@pytest.mark.parametrize("xp, level", [(0, 1), (99, 1), (100, 2), (299, 2), (300, 3), (600, 4)])
def test_levels(xp, level):
    assert level_from_xp(xp)["level"] == level


def test_quiz_xp():
    assert services.quiz_xp(0) == 5
    assert services.quiz_xp(55) == 10
    assert services.quiz_xp(100) == 15  # the perfect-score bonus is awarded separately, once


def test_weekly_leaderboard_is_per_grade_and_hides_surnames(client_for, student, other_student):
    from .conftest import make_user

    s4 = make_user("older", grade="S4")
    services.award_xp(student, 30, "test")
    services.award_xp(other_student, 50, "test")
    services.award_xp(s4, 500, "test")
    data = client_for(student).get("/api/leaderboard/").data
    assert [e["points"] for e in data["entries"]] == [50, 30]
    assert data["me"]["rank"] == 2 and data["me"]["name"] == "Aline U."


def test_leaderboard_class_scope_requires_membership(client_for, student, teacher):
    from apps.classroom.models import Classroom

    classroom = Classroom.objects.create(name="C", grade="S2", teacher=teacher)
    assert client_for(student).get(f"/api/leaderboard/?scope=class&classroom={classroom.id}").status_code == 404


def test_badges_endpoint(client_for, student):
    services.ensure_badges()
    services.award_badge(student, "first-lesson")
    data = client_for(student).get("/api/badges/").data
    earned = {b["code"] for b in data if b["earned"]}
    assert earned == {"first-lesson"}
    assert XPEvent.objects.count() == 0


def test_leaderboard_lists_top_50_and_ranks_everyone(client_for, student):
    from .conftest import make_user

    for i in range(55):
        services.award_xp(make_user(f"kid{i}"), 100 + i, "test")
    services.award_xp(student, 1, "test")
    for period in ("week", "all"):
        data = client_for(student).get("/api/leaderboard/", {"period": period}).data
        assert len(data["entries"]) == 50
        assert data["entries"][0]["points"] == 154
        assert "user_id" not in data["entries"][0]
        assert data["me"]["rank"] == 56 and data["me"]["points"] == 1


def test_teachers_only_see_class_leaderboards(client_for, teacher, student):
    services.award_xp(student, 10, "test")
    assert client_for(teacher).get("/api/leaderboard/").data["entries"] == []


def test_streak_shown_lapses_after_a_missed_day(client_for, student):
    from django.utils import timezone

    student.streak_days = 5
    student.last_active_date = timezone.localdate() - timedelta(days=1)
    student.save()
    assert client_for(student).get("/api/auth/me/").data["streak_days"] == 5
    student.last_active_date = timezone.localdate() - timedelta(days=2)
    student.save()
    assert client_for(student).get("/api/auth/me/").data["streak_days"] == 0
    assert client_for(student).get("/api/dashboard/").data["streak_days"] == 0
