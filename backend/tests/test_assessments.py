from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.assessments import services
from apps.assessments.models import Answer, Attempt, Choice, Question
from apps.classroom.models import Classroom, Enrollment

from .conftest import add_mcq, make_quiz

pytestmark = pytest.mark.django_db


def start(client, quiz):
    response = client.post(f"/api/quizzes/{quiz.id}/start/")
    assert response.status_code == 201, response.data
    return response.data


def correct_choice(question):
    return question.choices.get(is_correct=True).id


# --- Scoring rules --------------------------------------------------------------


def _answer(attempt, question, **fields):
    answer = Answer.objects.create(attempt=attempt, question=question, **{k: v for k, v in fields.items() if k != "choices"})
    if "choices" in fields:
        answer.selected_choices.set(fields["choices"])
    return answer


@pytest.fixture
def attempt(student, quiz_factory):
    return Attempt.objects.create(user=student, quiz=quiz_factory())


def test_mcq_scoring(attempt, subject, unit):
    q = add_mcq(subject, unit, marks=2)
    right = _answer(attempt, q, choices=[correct_choice(q)])
    assert services.score_answer(right) == (True, Decimal("2"))
    Answer.objects.all().delete()
    wrong = _answer(attempt, q, choices=[q.choices.filter(is_correct=False).first().id])
    assert services.score_answer(wrong) == (False, Decimal("0"))


def test_multi_select_gives_partial_credit_and_penalises_wrong_picks(attempt, subject, unit):
    q = Question.objects.create(subject=subject, grade="S2", type=Question.Type.MULTI, prompt="Pick primes", marks=2)
    two = Choice.objects.create(question=q, text="2", is_correct=True)
    three = Choice.objects.create(question=q, text="3", is_correct=True)
    four = Choice.objects.create(question=q, text="4", is_correct=False)

    assert services.score_answer(_answer(attempt, q, choices=[two.id, three.id])) == (True, Decimal("2.00"))
    Answer.objects.all().delete()
    assert services.score_answer(_answer(attempt, q, choices=[two.id])) == (False, Decimal("1.00"))
    Answer.objects.all().delete()
    assert services.score_answer(_answer(attempt, q, choices=[two.id, four.id])) == (False, Decimal("0.00"))


def test_numeric_tolerance(attempt, subject):
    q = Question.objects.create(
        subject=subject, grade="S2", type=Question.Type.NUMERIC, prompt="g?", numeric_answer=9.8, numeric_tolerance=0.1
    )
    assert services.score_answer(_answer(attempt, q, numeric_answer=9.75))[0] is True
    Answer.objects.all().delete()
    assert services.score_answer(_answer(attempt, q, numeric_answer=10.0))[0] is False


def test_short_answer_ignores_case_spacing_and_full_stop(attempt, subject):
    q = Question.objects.create(
        subject=subject, grade="S2", type=Question.Type.SHORT, prompt="Unit?", accepted_answers=["Sodium chloride"]
    )
    assert services.score_answer(_answer(attempt, q, text_answer="  sodium   CHLORIDE. "))[0] is True


def test_essay_needs_teacher(attempt, subject):
    q = Question.objects.create(subject=subject, grade="S2", type=Question.Type.ESSAY, prompt="Discuss")
    assert services.score_answer(_answer(attempt, q, text_answer="...")) == (None, None)


# --- Attempt lifecycle over the API ----------------------------------------------


def test_attempt_never_leaks_answers_before_submit(client_for, student, quiz_factory):
    quiz = quiz_factory(feedback_mode="after_submit")
    data = start(client_for(student), quiz)
    for question in data["questions"]:
        assert question["solution"] is None
        assert all(set(choice) == {"id", "text"} for choice in question["choices"])


def test_practice_check_reveals_solution_and_locks_answer(client_for, student, quiz_factory):
    quiz = quiz_factory(feedback_mode="immediate")
    client = client_for(student)
    attempt = start(client, quiz)
    question = Question.objects.get(pk=attempt["questions"][0]["id"])

    client.post(
        f"/api/attempts/{attempt['id']}/answer/",
        {"question": question.id, "choice_ids": [correct_choice(question)]},
        format="json",
    )
    checked = client.post(f"/api/attempts/{attempt['id']}/check/", {"question": question.id}, format="json")
    assert checked.status_code == 200
    assert checked.data["solution"]["is_correct"] is True
    assert checked.data["solution"]["explanation"] == "Because."

    wrong = question.choices.filter(is_correct=False).first().id
    response = client.post(
        f"/api/attempts/{attempt['id']}/answer/", {"question": question.id, "choice_ids": [wrong]}, format="json"
    )
    assert response.status_code == 400


def test_exam_mode_forbids_checking(client_for, student, quiz_factory):
    quiz = quiz_factory(feedback_mode="after_submit")
    client = client_for(student)
    attempt = start(client, quiz)
    response = client.post(f"/api/attempts/{attempt['id']}/check/", {"question": attempt["questions"][0]["id"]}, format="json")
    assert response.status_code == 403


def test_submit_scores_attempt_and_awards_xp(client_for, student, quiz_factory):
    quiz = quiz_factory()
    client = client_for(student)
    attempt = start(client, quiz)
    for q in attempt["questions"]:
        question = Question.objects.get(pk=q["id"])
        client.post(
            f"/api/attempts/{attempt['id']}/answer/",
            {"question": q["id"], "choice_ids": [correct_choice(question)]},
            format="json",
        )
    result = client.post(f"/api/attempts/{attempt['id']}/submit/").data
    assert result["status"] == "marked"
    assert Decimal(result["score"]) == Decimal("2")
    assert result["percentage"] == 100.0
    assert all(q["solution"]["is_correct"] for q in result["questions"])
    student.refresh_from_db()
    assert student.xp > 0
    assert student.badges.filter(badge__code="quiz-whiz").exists()


def test_resubmitting_does_not_double_award_xp(client_for, student, quiz_factory):
    quiz = quiz_factory()
    client = client_for(student)
    attempt = start(client, quiz)
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    xp = type(student).objects.get(pk=student.pk).xp
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    assert type(student).objects.get(pk=student.pk).xp == xp


def test_order_is_fixed_per_attempt(client_for, student, quiz_factory):
    quiz = quiz_factory()
    client = client_for(student)
    first = start(client, quiz)
    again = client.get(f"/api/attempts/{first['id']}/").data
    assert [q["id"] for q in first["questions"]] == [q["id"] for q in again["questions"]]
    assert [c["id"] for c in first["questions"][0]["choices"]] == [c["id"] for c in again["questions"][0]["choices"]]
    # Starting again resumes the same in-progress attempt.
    assert start(client, quiz)["id"] == first["id"]


def test_rejects_questions_and_choices_from_elsewhere(client_for, student, quiz_factory, subject, unit):
    quiz = quiz_factory()
    outsider = add_mcq(subject, unit, "Not in quiz")
    client = client_for(student)
    attempt = start(client, quiz)
    url = f"/api/attempts/{attempt['id']}/answer/"
    assert client.post(url, {"question": outsider.id, "choice_ids": [correct_choice(outsider)]}, format="json").status_code == 400
    in_quiz = attempt["questions"][0]["id"]
    assert client.post(url, {"question": in_quiz, "choice_ids": [correct_choice(outsider)]}, format="json").status_code == 400


def test_timed_attempt_closes_after_deadline(client_for, student, quiz_factory, settings):
    settings.EXAM_SUBMIT_GRACE_SECONDS = 0
    quiz = quiz_factory(time_limit_minutes=10, feedback_mode="after_submit")
    client = client_for(student)
    attempt = start(client, quiz)
    Attempt.objects.filter(pk=attempt["id"]).update(deadline=timezone.now() - timedelta(seconds=5))

    response = client.post(
        f"/api/attempts/{attempt['id']}/answer/", {"question": attempt["questions"][0]["id"], "choice_ids": []}, format="json"
    )
    assert response.status_code == 400
    assert Attempt.objects.get(pk=attempt["id"]).status == "marked"


def test_expired_attempt_is_finalised_when_viewed(client_for, student, quiz_factory, settings):
    settings.EXAM_SUBMIT_GRACE_SECONDS = 0
    quiz = quiz_factory(time_limit_minutes=5)
    client = client_for(student)
    attempt = start(client, quiz)
    Attempt.objects.filter(pk=attempt["id"]).update(deadline=timezone.now() - timedelta(minutes=1))
    assert client.get(f"/api/attempts/{attempt['id']}/").data["status"] == "marked"


def test_max_attempts(client_for, student, quiz_factory):
    quiz = quiz_factory(max_attempts=1)
    client = client_for(student)
    attempt = start(client, quiz)
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    assert client.post(f"/api/quizzes/{quiz.id}/start/").status_code == 403


def test_students_cannot_open_other_students_attempts(client_for, student, other_student, quiz_factory):
    attempt = start(client_for(student), quiz_factory())
    assert client_for(other_student).get(f"/api/attempts/{attempt['id']}/").status_code == 404


def test_students_cannot_reach_question_bank(client_for, student):
    assert client_for(student).get("/api/questions/").status_code == 403


def test_draft_quizzes_hidden_unless_assigned(client_for, student, teacher, quiz_factory):
    quiz = quiz_factory(status="draft", author=teacher)
    client = client_for(student)
    assert client.post(f"/api/quizzes/{quiz.id}/start/").status_code == 404
    classroom = Classroom.objects.create(name="C", grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=student)
    classroom.assignments.create(title="Do it", quiz=quiz, created_by=teacher)
    assert client.post(f"/api/quizzes/{quiz.id}/start/").status_code == 201


# --- Teacher marking --------------------------------------------------------------


@pytest.fixture
def essay_quiz(subject, unit):
    essay = Question.objects.create(
        subject=subject, grade="S2", unit=unit, type=Question.Type.ESSAY, prompt="Explain", marks=4, marking_guide="Key points"
    )
    return make_quiz(subject, unit, [add_mcq(subject, unit), essay], feedback_mode="after_submit")


def test_written_answers_go_to_teacher_marking(client_for, student, teacher, other_teacher, essay_quiz):
    classroom = Classroom.objects.create(name="C", grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=student)

    client = client_for(student)
    attempt = start(client, essay_quiz)
    essay_id = next(q["id"] for q in attempt["questions"] if q["type"] == "essay")
    client.post(f"/api/attempts/{attempt['id']}/answer/", {"question": essay_id, "text": "My answer"}, format="json")
    result = client.post(f"/api/attempts/{attempt['id']}/submit/").data
    assert result["status"] == "needs_marking"

    queue = client_for(teacher).get("/api/marking/").data
    assert len(queue) == 1 and queue[0]["answer_text"] == "My answer"
    answer_id = queue[0]["id"]

    assert client_for(other_teacher).get("/api/marking/").data == []
    assert client_for(other_teacher).post(f"/api/marking/{answer_id}/mark/", {"marks": 4}, format="json").status_code == 404
    assert client_for(teacher).post(f"/api/marking/{answer_id}/mark/", {"marks": 5}, format="json").status_code == 400

    response = client_for(teacher).post(f"/api/marking/{answer_id}/mark/", {"marks": 3, "feedback": "Good"}, format="json")
    assert response.status_code == 200
    final = client.get(f"/api/attempts/{attempt['id']}/").data
    assert final["status"] == "marked"
    essay = next(q for q in final["questions"] if q["type"] == "essay")
    assert essay["solution"]["teacher_feedback"] == "Good"


def test_teacher_quiz_publish_requires_admin_review(client_for, teacher, subject, unit):
    q = add_mcq(subject, unit)
    response = client_for(teacher).post(
        "/api/quizzes/",
        {"title": "My quiz", "subject": subject.id, "grade": "S2", "status": "published", "question_ids": [q.id]},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == "review"


def test_only_admin_can_create_past_papers(client_for, teacher, subject):
    response = client_for(teacher).post(
        "/api/quizzes/", {"title": "Fake paper", "subject": subject.id, "grade": "S3", "kind": "past_paper"}, format="json"
    )
    assert response.status_code == 400


def test_question_validation(client_for, teacher, subject):
    client = client_for(teacher)
    base = {"subject": subject.id, "grade": "S2", "type": "mcq", "prompt": "?"}
    assert (
        client.post("/api/questions/", {**base, "choices": [{"text": "a", "is_correct": True}]}, format="json").status_code == 400
    )
    two_right = [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]
    assert client.post("/api/questions/", {**base, "choices": two_right}, format="json").status_code == 400
    ok = [{"text": "a", "is_correct": True}, {"text": "b"}]
    assert client.post("/api/questions/", {**base, "choices": ok}, format="json").status_code == 201


def test_blank_written_answers_score_zero_without_teacher(client_for, student, teacher, essay_quiz):
    classroom = Classroom.objects.create(name="C", grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=student)
    client = client_for(student)
    attempt = start(client, essay_quiz)
    result = client.post(f"/api/attempts/{attempt['id']}/submit/").data
    assert result["status"] == "marked"
    assert client_for(teacher).get("/api/marking/").data == []
