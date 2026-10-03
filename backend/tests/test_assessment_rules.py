"""Fairness rules: marking scope, answer-key locks, attempt races and quiz XP."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.assessments import services
from apps.assessments.models import Attempt, Question
from apps.classroom.models import Assignment, Classroom, Enrollment
from apps.curriculum.models import Subject

from .conftest import add_mcq, make_quiz

pytestmark = pytest.mark.django_db


def start(client, quiz, **data):
    response = client.post(f"/api/quizzes/{quiz.id}/start/", data, format="json")
    assert response.status_code == 201, response.data
    return response.data


def answer_all_correctly(client, attempt):
    for q in attempt["questions"]:
        question = Question.objects.get(pk=q["id"])
        client.post(
            f"/api/attempts/{attempt['id']}/answer/",
            {"question": q["id"], "choice_ids": [question.choices.get(is_correct=True).id]},
            format="json",
        )


def xp(user):
    return type(user).objects.get(pk=user.pk).xp


# --- XP ---------------------------------------------------------------------------


def test_quiz_xp_is_earned_once_per_quiz(client_for, student, quiz_factory):
    quiz = quiz_factory()
    client = client_for(student)
    attempt = start(client, quiz)
    answer_all_correctly(client, attempt)
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    after_first = xp(student)
    assert after_first == 15 + 10  # quiz XP at 100% plus the one-off perfect bonus

    again = start(client, quiz)
    answer_all_correctly(client, again)
    client.post(f"/api/attempts/{again['id']}/submit/")
    assert xp(student) == after_first


def test_blank_attempts_earn_nothing(client_for, student, quiz_factory):
    quiz = quiz_factory()
    client = client_for(student)
    attempt = start(client, quiz)
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    assert xp(student) == 0
    # ...and don't use up the quiz's XP either.
    real = start(client, quiz)
    answer_all_correctly(client, real)
    client.post(f"/api/attempts/{real['id']}/submit/")
    assert xp(student) == 25


def test_perfect_bonus_after_an_imperfect_first_try(client_for, student, quiz_factory):
    quiz = quiz_factory()
    client = client_for(student)
    first = start(client, quiz)
    q = first["questions"][0]
    wrong = Question.objects.get(pk=q["id"]).choices.filter(is_correct=False).first().id
    client.post(f"/api/attempts/{first['id']}/answer/", {"question": q["id"], "choice_ids": [wrong]}, format="json")
    client.post(f"/api/attempts/{first['id']}/submit/")
    assert xp(student) == 5
    second = start(client, quiz)
    answer_all_correctly(client, second)
    client.post(f"/api/attempts/{second['id']}/submit/")
    assert xp(student) == 5 + 10


# --- Starting attempts --------------------------------------------------------------


def test_starting_twice_returns_the_same_attempt_and_attaches_the_assignment(client_for, student, teacher, quiz_factory):
    quiz = quiz_factory()
    classroom = Classroom.objects.create(name="C", grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=student)
    assignment = Assignment.objects.create(classroom=classroom, quiz=quiz, title="Homework", created_by=teacher)
    client = client_for(student)
    first = start(client, quiz)
    second = start(client, quiz, assignment=assignment.id)
    assert first["id"] == second["id"]
    assert Attempt.objects.get(pk=first["id"]).assignment_id == assignment.id
    assert Attempt.objects.filter(user=student, quiz=quiz).count() == 1


def test_assignment_must_be_valid_and_current(client_for, student, teacher, quiz_factory):
    quiz = quiz_factory()
    classroom = Classroom.objects.create(name="C", grade="S2", teacher=teacher, archived=True)
    Enrollment.objects.create(classroom=classroom, student=student)
    assignment = Assignment.objects.create(classroom=classroom, quiz=quiz, title="Old", created_by=teacher)
    client = client_for(student)
    assert client.post(f"/api/quizzes/{quiz.id}/start/", {"assignment": "abc"}, format="json").status_code == 400
    assert client.post(f"/api/quizzes/{quiz.id}/start/", {"assignment": assignment.id}, format="json").status_code == 404


def test_database_allows_only_one_open_attempt(student, quiz_factory):
    from django.db import IntegrityError, transaction

    quiz = quiz_factory()
    Attempt.objects.create(user=student, quiz=quiz)
    with pytest.raises(IntegrityError), transaction.atomic():
        Attempt.objects.create(user=student, quiz=quiz)


def test_expired_attempt_is_submitted_even_when_no_attempts_remain(client_for, student, quiz_factory):
    quiz = quiz_factory(max_attempts=1, time_limit_minutes=5)
    client = client_for(student)
    attempt = start(client, quiz)
    Attempt.objects.filter(pk=attempt["id"]).update(
        started_at=timezone.now() - timedelta(hours=1), deadline=timezone.now() - timedelta(minutes=30)
    )
    assert client.post(f"/api/quizzes/{quiz.id}/start/").status_code == 403
    assert Attempt.objects.get(pk=attempt["id"]).status != Attempt.Status.IN_PROGRESS


def test_answers_cannot_be_saved_after_submit(student, quiz_factory):
    quiz = quiz_factory()
    attempt = services.start_attempt(student, quiz)
    stale = Attempt.objects.get(pk=attempt.pk)  # e.g. a request that loaded the attempt before submit
    services.submit_attempt(attempt)
    question_id = attempt.question_order[0]
    with pytest.raises(Exception, match="already been submitted"):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(services, "_ensure_open", lambda a: None)  # skip the early check to hit the row lock
            services.save_answer(stale, question_id, choice_ids=[])


# --- Scoring -----------------------------------------------------------------------


def test_numeric_tolerance_scales_with_magnitude(student, subject, unit):
    q = Question.objects.create(
        subject=subject, grade="S2", unit=unit, type=Question.Type.NUMERIC, prompt="N_A?", numeric_answer=6.02e23
    )
    quiz = make_quiz(subject, unit, [q])
    attempt = Attempt.objects.create(user=student, quiz=quiz, question_order=[q.id])
    from apps.assessments.models import Answer

    answer = Answer.objects.create(attempt=attempt, question=q, numeric_answer=6.02e23 * (1 + 1e-12))
    assert services.score_answer(answer)[0] is True


def test_accepted_answers_must_be_a_list_of_text(client_for, teacher, subject):
    client = client_for(teacher)
    base = {"subject": subject.id, "grade": "S2", "type": "short", "prompt": "Symbol for water?"}
    assert client.post("/api/questions/", {**base, "accepted_answers": "H2O"}, format="json").status_code == 400
    assert client.post("/api/questions/", {**base, "accepted_answers": [1, 2]}, format="json").status_code == 400
    ok = client.post("/api/questions/", {**base, "accepted_answers": [" H2O ", ""]}, format="json")
    assert ok.status_code == 201 and ok.data["accepted_answers"] == ["H2O"]


# --- Editing content students have used ----------------------------------------------


def test_answer_key_is_locked_once_students_answer(client_for, teacher, student, subject, unit):
    question = add_mcq(subject, unit)
    question.author = teacher
    question.save()
    quiz = make_quiz(subject, unit, [question])
    attempt = services.start_attempt(student, quiz)
    services.save_answer(attempt, question.id, choice_ids=[question.choices.get(is_correct=True).id])

    client = client_for(teacher)
    options = list(question.choices.order_by("order", "id"))
    flipped = [{"text": c.text, "is_correct": not c.is_correct} for c in options]
    assert client.patch(f"/api/questions/{question.id}/", {"choices": flipped}, format="json").status_code == 400
    assert client.patch(f"/api/questions/{question.id}/", {"marks": 5}, format="json").status_code == 400

    reworded = [{"text": c.text + " (units)", "is_correct": c.is_correct} for c in options]
    response = client.patch(f"/api/questions/{question.id}/", {"prompt": "What is 2 + 2?", "choices": reworded}, format="json")
    assert response.status_code == 200
    # The same option rows were kept, so the student's selection survives.
    assert attempt.answers.get().selected_choices.count() == 1
    assert set(question.choices.values_list("id", flat=True)) == {c.id for c in options}


def test_editing_a_published_quiz_sends_it_back_to_review(client_for, teacher, subject, unit):
    quiz = make_quiz(subject, unit, [add_mcq(subject, unit)], author=teacher, status="published")
    response = client_for(teacher).patch(f"/api/quizzes/{quiz.id}/", {"title": "Renamed"}, format="json")
    assert response.status_code == 200
    quiz.refresh_from_db()
    assert quiz.status == "review"


def test_quiz_questions_cannot_change_after_attempts(client_for, teacher, student, subject, unit):
    q1, q2 = add_mcq(subject, unit), add_mcq(subject, unit, "1 + 1?", "2", ("3", "4"))
    quiz = make_quiz(subject, unit, [q1], author=teacher, status="draft")
    services.start_attempt(student, quiz)
    client = client_for(teacher)
    assert client.patch(f"/api/quizzes/{quiz.id}/", {"question_ids": [q1.id, q2.id]}, format="json").status_code == 400
    # Re-sending the same list (as the editor does when saving other fields) is fine.
    assert client.patch(f"/api/quizzes/{quiz.id}/", {"question_ids": [q1.id], "title": "T"}, format="json").status_code == 200


# --- Who marks what -------------------------------------------------------------------


@pytest.fixture
def essay_quiz(subject, unit):
    essay = Question.objects.create(subject=subject, grade="S2", unit=unit, type=Question.Type.ESSAY, prompt="Explain", marks=4)
    return make_quiz(subject, unit, [add_mcq(subject, unit), essay], feedback_mode="after_submit")


def submit_essay(client, quiz, **start_data):
    attempt = start(client, quiz, **start_data)
    essay_id = next(q["id"] for q in attempt["questions"] if q["type"] == "essay")
    client.post(f"/api/attempts/{attempt['id']}/answer/", {"question": essay_id, "text": "Because..."}, format="json")
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    return attempt


def test_teachers_mark_only_their_subject_or_their_assignments(client_for, student, teacher, other_teacher, subject, essay_quiz):
    chemistry = Subject.objects.create(code="chemistry", name="Chemistry")
    maths_class = Classroom.objects.create(name="Maths", grade="S2", teacher=teacher, subject=subject)
    chem_class = Classroom.objects.create(name="Chem", grade="S2", teacher=other_teacher, subject=chemistry)
    for c in (maths_class, chem_class):
        Enrollment.objects.create(classroom=c, student=student)

    submit_essay(client_for(student), essay_quiz)
    assert len(client_for(teacher).get("/api/marking/").data) == 1
    assert client_for(other_teacher).get("/api/marking/").data == []  # a chemistry teacher can't mark maths work

    # ...unless they set it as an assignment in their class.
    essay_quiz2 = make_quiz(subject, essay_quiz.unit, list(essay_quiz.questions.all()), feedback_mode="after_submit")
    assignment = Assignment.objects.create(classroom=chem_class, quiz=essay_quiz2, title="Cross-topic", created_by=other_teacher)
    submit_essay(client_for(student), essay_quiz2, assignment=assignment.id)
    assert len(client_for(other_teacher).get("/api/marking/").data) == 1


def test_archived_classes_no_longer_grant_access(client_for, student, teacher, essay_quiz):
    classroom = Classroom.objects.create(name="Old", grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=student)
    attempt = submit_essay(client_for(student), essay_quiz)
    classroom.archived = True
    classroom.save()
    assert client_for(teacher).get("/api/marking/").data == []
    assert client_for(teacher).get(f"/api/attempts/{attempt['id']}/").status_code == 404


def test_auto_marked_answers_cannot_be_overridden(client_for, student, teacher, essay_quiz):
    classroom = Classroom.objects.create(name="C", grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=student)
    attempt = submit_essay(client_for(student), essay_quiz)
    mcq_answer = Attempt.objects.get(pk=attempt["id"]).answers.get(question__type="mcq")
    response = client_for(teacher).post(f"/api/marking/{mcq_answer.id}/mark/", {"marks": 1}, format="json")
    assert response.status_code == 404
