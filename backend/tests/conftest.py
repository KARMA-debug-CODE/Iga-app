import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.assessments.models import Choice, Question, Quiz, QuizQuestion
from apps.curriculum.models import Lesson, Subject, Unit


@pytest.fixture(autouse=True)
def _no_throttling(settings):
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {"auth": "1000/min", "chat": "1000/min"},
    }


def make_user(username, role=User.Role.STUDENT, grade="S2", **extra):
    user = User.objects.create_user(
        username=username,
        password="Str0ng-pass-123",
        email=f"{username}@example.com",
        role=role,
        grade=grade if role == User.Role.STUDENT else "",
        **extra,
    )
    return user


@pytest.fixture
def student(db):
    return make_user("student", first_name="Aline", last_name="Uwase")


@pytest.fixture
def other_student(db):
    return make_user("other")


@pytest.fixture
def teacher(db):
    return make_user("teacher", role=User.Role.TEACHER, teacher_approved=True)


@pytest.fixture
def other_teacher(db):
    return make_user("teacher2", role=User.Role.TEACHER, teacher_approved=True)


@pytest.fixture
def admin_user(db):
    return make_user("admin", role=User.Role.ADMIN)


@pytest.fixture
def client_for():
    def _client(user=None):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client

    return _client


@pytest.fixture
def subject(db):
    return Subject.objects.create(code="mathematics", name="Mathematics", name_sw="Hisabati")


@pytest.fixture
def unit(subject):
    return Unit.objects.create(subject=subject, grade="S2", number=1, title="Linear graphs")


@pytest.fixture
def lesson(unit):
    return Lesson.objects.create(unit=unit, slug="linear", title="Linear graphs", body="# Hello", status="published")


def add_mcq(subject, unit, prompt="2 + 2?", correct="4", wrong=("3", "5"), marks=1):
    q = Question.objects.create(
        subject=subject, grade=unit.grade, unit=unit, type=Question.Type.MCQ, prompt=prompt, marks=marks, explanation="Because."
    )
    Choice.objects.create(question=q, text=correct, is_correct=True)
    for text in wrong:
        Choice.objects.create(question=q, text=text, is_correct=False)
    return q


def make_quiz(subject, unit, questions, **kwargs):
    defaults = {"title": "Quiz", "grade": unit.grade, "status": "published"}
    defaults.update(kwargs)
    quiz = Quiz.objects.create(subject=subject, unit=unit, **defaults)
    for i, q in enumerate(questions):
        QuizQuestion.objects.create(quiz=quiz, question=q, order=i)
    return quiz


@pytest.fixture
def quiz_factory(subject, unit):
    def _make(questions=None, **kwargs):
        if questions is None:
            questions = [add_mcq(subject, unit), add_mcq(subject, unit, "3 + 3?", "6", ("5", "7"))]
        return make_quiz(subject, unit, questions, **kwargs)

    return _make
