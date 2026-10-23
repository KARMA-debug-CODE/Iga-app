"""Teaching Packs: assigning a pack's quiz or a worksheet level to its class."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import Attempt, Question, Quiz
from apps.classroom.models import Assignment

from .conftest import add_mcq, make_school, make_user
from .teaching_factories import class_with_students

PACKS = "/api/teaching/packs/"


@pytest.fixture
def setup(teacher, subject, unit):
    classroom, students = class_with_students(teacher, subject, 5)
    questions = [add_mcq(subject, unit, f"q{i}?") for i in range(4)]
    return {"classroom": classroom, "students": students, "questions": questions}


def make_pack(client_for, teacher, classroom, unit):
    response = client_for(teacher).post(PACKS, {"classroom": classroom.id, "unit": unit.id}, format="json")
    assert response.status_code == 201, response.content
    return response.json()


def assign(client_for, teacher, pack_id, what="quiz", **extra):
    return client_for(teacher).post(f"{PACKS}{pack_id}/assign/", {"what": what, **extra}, format="json")


def test_assigning_the_quiz_creates_a_quiz_and_an_assignment(client_for, teacher, unit, setup):
    pack = make_pack(client_for, teacher, setup["classroom"], unit)
    due = (timezone.now() + timedelta(days=3)).replace(microsecond=0)
    response = assign(client_for, teacher, pack["id"], due_at=due.isoformat())
    assert response.status_code == 201
    body = response.json()
    assert (body["what"], body["dropped"], body["created"]) == ("quiz", 0, True)
    quiz = Quiz.objects.get(pk=body["quiz_id"])
    expected = [q["id"] for q in pack["document"]["quiz"]["questions"]]
    assert list(quiz.quiz_questions.order_by("order").values_list("question_id", flat=True)) == expected
    assert (quiz.author, quiz.is_free, quiz.status, quiz.unit, quiz.subject) == (teacher, False, "published", unit, unit.subject)
    assignment = Assignment.objects.get(pk=body["assignment_id"])
    assert (assignment.classroom, assignment.quiz, assignment.created_by, assignment.due_at) == (
        setup["classroom"],
        quiz,
        teacher,
        due,
    )


def test_assigning_twice_returns_the_same_assignment(client_for, teacher, unit, setup):
    pack = make_pack(client_for, teacher, setup["classroom"], unit)
    first = assign(client_for, teacher, pack["id"]).json()
    quizzes = Quiz.objects.count()
    again = assign(client_for, teacher, pack["id"])
    assert again.status_code == 200
    assert again.json()["assignment_id"] == first["assignment_id"] and again.json()["created"] is False
    assert Quiz.objects.count() == quizzes


def test_assigning_a_worksheet_level_uses_that_level(client_for, teacher, unit, setup):
    pack = make_pack(client_for, teacher, setup["classroom"], unit)
    body = assign(client_for, teacher, pack["id"], what="worksheet_core").json()
    expected = [q["id"] for q in pack["document"]["worksheet"]["core"]]
    quiz = Quiz.objects.get(pk=body["quiz_id"])
    assert list(quiz.quiz_questions.order_by("order").values_list("question_id", flat=True)) == expected


def test_unpublished_questions_are_dropped_and_reported(client_for, teacher, unit, setup):
    pack = make_pack(client_for, teacher, setup["classroom"], unit)
    Question.objects.filter(pk=setup["questions"][0].pk).update(status="draft")
    body = assign(client_for, teacher, pack["id"]).json()
    assert body["dropped"] == 1
    assert setup["questions"][0].id not in Quiz.objects.get(pk=body["quiz_id"]).questions.values_list("id", flat=True)


def test_nothing_left_to_assign(client_for, teacher, unit, setup):
    pack = make_pack(client_for, teacher, setup["classroom"], unit)
    Question.objects.filter(unit=unit).update(status="draft")
    response = assign(client_for, teacher, pack["id"])
    assert response.status_code == 400 and response.json()["code"] == "nothing_to_assign"
    assert not Assignment.objects.exists()


def test_unknown_parts_are_refused(client_for, teacher, unit, setup):
    pack = make_pack(client_for, teacher, setup["classroom"], unit)
    assert assign(client_for, teacher, pack["id"], what="everything").status_code == 400


def test_students_can_take_the_assigned_quiz(client_for, teacher, unit, setup):
    pack = make_pack(client_for, teacher, setup["classroom"], unit)
    body = assign(client_for, teacher, pack["id"]).json()
    student = setup["students"][0]
    client = client_for(student)
    listed = client.get("/api/assignments/").json()
    rows = listed["results"] if isinstance(listed, dict) else listed
    assert body["assignment_id"] in [row["id"] for row in rows]
    attempt = client.post(f"/api/quizzes/{body['quiz_id']}/start/", {"assignment": body["assignment_id"]}, format="json").json()
    question = Question.objects.get(pk=pack["document"]["quiz"]["questions"][0]["id"])
    right = question.choices.get(is_correct=True).id
    client.post(f"/api/attempts/{attempt['id']}/answer/", {"question": question.id, "choice_ids": [right]}, format="json")
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    assert Attempt.objects.get(pk=attempt["id"]).status == Attempt.Status.MARKED


def test_lapsed_or_archived_cannot_assign(client_for, subject, unit):
    school = make_school("Lapsing", paid_until=timezone.now() + timedelta(days=10))
    lapsing = make_user("lapsing", role=User.Role.TEACHER, teacher_approved=True, school=school)
    classroom, _students = class_with_students(lapsing, subject, 2, prefix="lp")
    add_mcq(subject, unit)
    pack = make_pack(client_for, lapsing, classroom, unit)
    classroom.archived = True
    classroom.save()
    archived = assign(client_for, lapsing, pack["id"])
    assert archived.status_code == 400 and archived.json()["code"] == "class_archived"
    classroom.archived = False
    classroom.save()
    school.paid_until = timezone.now() - timedelta(days=60)
    school.save()
    assert assign(client_for, User.objects.get(pk=lapsing.pk), pack["id"]).status_code == 403
