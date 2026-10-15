"""The PWA keeps lessons and the student's profile on the device, and sends answers, completions and
lab visits back. A device can be tampered with (its storage edited, its requests replayed or
forged), so the server recomputes everything and believes nothing but the choice itself (S45)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.assessments.models import Answer, Attempt, Question
from apps.gamification.models import XPEvent
from apps.simulations.models import Simulation, SimulationView

from .conftest import add_mcq, make_quiz, make_user

pytestmark = pytest.mark.django_db


def start(client, quiz, body=None):
    response = client.post(f"/api/quizzes/{quiz.id}/start/", body or {}, format="json")
    assert response.status_code == 201, response.data
    return response.data


def wrong_choice(question_payload):
    correct = Question.objects.get(pk=question_payload["id"]).choices.filter(is_correct=True).values_list("id", flat=True)
    return next(c["id"] for c in question_payload["choices"] if c["id"] not in correct)


def test_a_forged_answer_cannot_mark_itself_right(client_for, student, quiz_factory):
    quiz = quiz_factory(feedback_mode="after_submit")
    client = client_for(student)
    attempt = start(client, quiz)
    for q in attempt["questions"]:
        forged = {
            "question": q["id"],
            "choice_ids": [wrong_choice(q)],
            "is_correct": True,
            "marks_awarded": 99,
            "checked": True,
            "score": 100,
            "percentage": 100,
            "xp": 5000,
        }
        assert client.post(f"/api/attempts/{attempt['id']}/answer/", forged, format="json").status_code == 200
    result = client.post(f"/api/attempts/{attempt['id']}/submit/", {"score": "2.00", "status": "marked"}, format="json").data
    assert result["score"] == "0.00"
    assert not Answer.objects.filter(is_correct=True).exists()
    student.refresh_from_db()
    assert student.xp == 5  # the base XP for finishing, computed on the server


def test_answers_the_app_could_never_send_are_refused(client_for, student, subject, unit):
    numeric = Question.objects.create(
        subject=subject, grade=unit.grade, unit=unit, type=Question.Type.NUMERIC, prompt="6 x 7?", numeric_answer=42
    )
    mcq = add_mcq(subject, unit)
    stranger = add_mcq(subject, unit, "Not in this quiz?")
    quiz = make_quiz(subject, unit, [mcq, numeric], feedback_mode="after_submit")
    client = client_for(student)
    attempt = start(client, quiz)
    url = f"/api/attempts/{attempt['id']}/answer/"
    mcq_ids = list(mcq.choices.values_list("id", flat=True))
    forged = [
        {"question": stranger.id, "choice_ids": [stranger.choices.first().id]},  # not in this attempt
        {"question": mcq.id, "choice_ids": [stranger.choices.first().id]},  # another question's option
        {"question": mcq.id, "choice_ids": mcq_ids},  # every option of a one-answer question
        {"question": mcq.id, "choice_ids": list(range(1, 52))},  # far more options than any question has
        {"question": mcq.id, "choice_ids": "1,2"},
        {"question": numeric.id, "numeric": "NaN"},
        {"question": numeric.id, "numeric": "Infinity"},
        {"question": numeric.id, "numeric": "1e400"},
        {"question": numeric.id, "numeric": "forty-two"},
        {"question": numeric.id, "text": "x" * 10001},
        {"question": "1 OR 1=1", "choice_ids": []},
    ]
    for body in forged:
        assert client.post(url, body, format="json").status_code == 400, body
    assert not Answer.objects.exclude(numeric_answer=None).exists()
    assert not Answer.objects.filter(selected_choices__isnull=False).exists()


def test_saves_replayed_after_the_submit_are_refused(client_for, student, quiz_factory):
    quiz = quiz_factory()
    client = client_for(student)
    attempt = start(client, quiz)
    q = attempt["questions"][0]
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    late = client.post(
        f"/api/attempts/{attempt['id']}/answer/", {"question": q["id"], "choice_ids": [q["choices"][0]["id"]]}, format="json"
    )
    assert late.status_code == 400 and late.data["code"] == "attempt_closed"
    assert client.post(f"/api/attempts/{attempt['id']}/check/", {"question": q["id"]}, format="json").status_code == 400
    again = client.post(f"/api/attempts/{attempt['id']}/submit/")
    assert again.status_code == 200 and Attempt.objects.get().submitted_at == Attempt.objects.get().submitted_at


def test_a_save_held_back_past_the_deadline_cannot_beat_the_clock(client_for, student, quiz_factory, settings):
    settings.EXAM_SUBMIT_GRACE_SECONDS = 30
    quiz = quiz_factory(time_limit_minutes=10, feedback_mode="after_submit")
    client = client_for(student)
    attempt = start(client, quiz)
    q = attempt["questions"][0]
    deadline = timezone.now() - timedelta(minutes=5)
    Attempt.objects.filter(pk=attempt["id"]).update(deadline=deadline, started_at=deadline - timedelta(minutes=10))
    late = client.post(
        f"/api/attempts/{attempt['id']}/answer/", {"question": q["id"], "choice_ids": [q["choices"][0]["id"]]}, format="json"
    )
    assert late.status_code == 400 and late.data["code"] in ("time_up", "attempt_closed")
    closed = Attempt.objects.get(pk=attempt["id"])
    assert closed.status != "in_progress" and closed.submitted_at == deadline  # the server's clock, not the device's
    assert not Answer.objects.filter(selected_choices__isnull=False).exists()


def test_the_device_cannot_choose_its_own_start_time_or_time_limit(client_for, student, quiz_factory):
    quiz = quiz_factory(time_limit_minutes=10)
    before = timezone.now()
    attempt = start(
        client_for(student),
        quiz,
        {"started_at": "2020-01-01T00:00:00Z", "deadline": "2099-01-01T00:00:00Z", "time_limit_minutes": 999},
    )
    saved = Attempt.objects.get(pk=attempt["id"])
    assert before <= saved.started_at <= timezone.now()
    assert saved.deadline == saved.started_at + timedelta(minutes=10)


def test_a_checked_practice_answer_cannot_be_swapped_for_the_right_one(client_for, student, quiz_factory):
    quiz = quiz_factory(feedback_mode="immediate")
    client = client_for(student)
    attempt = start(client, quiz)
    q = attempt["questions"][0]
    url = f"/api/attempts/{attempt['id']}/answer/"
    client.post(url, {"question": q["id"], "choice_ids": [wrong_choice(q)]}, format="json")
    checked = client.post(f"/api/attempts/{attempt['id']}/check/", {"question": q["id"]}, format="json").data
    right = Question.objects.get(pk=q["id"]).choices.get(is_correct=True).id
    assert client.post(url, {"question": q["id"], "choice_ids": [right]}, format="json").status_code == 400
    result = client.post(f"/api/attempts/{attempt['id']}/submit/").data
    assert checked["answer"]["checked"] is True and checked["solution"]["is_correct"] is False
    assert result["score"] == "0.00"


def test_replayed_completions_and_lab_visits_count_once(client_for, student, lesson):
    client = client_for(student)
    first = client.post(f"/api/lessons/{lesson.slug}/complete/", {"xp": 1000, "completed_at": "2020-01-01"}, format="json")
    assert first.data["xp_gained"] == 10
    for _ in range(5):
        assert client.post(f"/api/lessons/{lesson.slug}/complete/").data["xp_gained"] == 0
    sim = Simulation.objects.create(slug="circuit", title="Circuit", provider="phet", provider_id="circuit-construction-kit-dc")
    gained = [client.post(f"/api/simulations/{sim.slug}/view/", {"xp": 1000}, format="json").data["xp_gained"] for _ in range(20)]
    assert gained == [5] + [0] * 19
    assert SimulationView.objects.filter(user=student, simulation=sim).count() == 1  # a replay flood adds no rows
    student.refresh_from_db()
    assert student.xp == 15 and XPEvent.objects.filter(user=student).count() == 2
    # A real visit later on is still counted for the teacher's gradebook.
    SimulationView.objects.filter(user=student).update(viewed_at=timezone.now() - timedelta(hours=1))
    client.post(f"/api/simulations/{sim.slug}/view/")
    assert SimulationView.objects.filter(user=student, simulation=sim).count() == 2


def test_a_device_cannot_award_itself_xp_streaks_or_premium_access(client_for, lesson):
    pupil = make_user("pupil", school=None)  # no school, so no subscription
    client = client_for(pupil)
    client.patch(
        "/api/auth/me/",
        {"xp": 99999, "streak_days": 365, "school_status": "approved", "role": "admin", "is_staff": True},
        format="json",
    )
    pupil.refresh_from_db()
    assert (pupil.xp, pupil.streak_days, pupil.role, pupil.is_staff) == (0, 0, "student", False)
    assert pupil.school_status != "approved"
    # A copy of a premium lesson kept on the device doesn't make it completable for XP.
    assert client.post(f"/api/lessons/{lesson.slug}/complete/").status_code == 403
    assert not XPEvent.objects.filter(user=pupil).exists()
