from datetime import timedelta

import pytest
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts.models import User
from apps.assessments.models import Choice, Question, Quiz, QuizQuestion
from apps.curriculum.models import Lesson, Subject, Unit
from apps.schools.models import School

# Every scope in the settings (new ones included), at a rate no test reaches by accident.
RELAXED_RATES = {scope: "1000/min" for scope in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]}


@pytest.fixture(autouse=True)
def _no_throttling(monkeypatch):
    # DRF reads rates into the throttle class at import time, so patch the class.
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", RELAXED_RATES)
    cache.clear()


_SUBSCRIBED = object()


def subscribed_school():
    """A verified school paid well into the future, shared by the default test users."""
    school, _ = School.objects.get_or_create(
        name="Test Subscribed School",
        district="Gasabo",
        defaults={"status": School.Status.VERIFIED, "paid_until": timezone.now() + timedelta(days=365)},
    )
    return school


def make_school(name="APADE", district="Kicukiro", paid_until=None, status=None):
    return School.objects.create(name=name, district=district, status=status or School.Status.VERIFIED, paid_until=paid_until)


def make_user(username, role=User.Role.STUDENT, grade="S2", school=_SUBSCRIBED, **extra):
    """Students and teachers belong to a subscribed school unless `school` says otherwise
    (pass school=None for someone without a school, or another School)."""
    user = User.objects.create_user(
        username=username,
        password="Str0ng-pass-123",
        email=f"{username}@example.com",
        role=role,
        grade=grade if role == User.Role.STUDENT else "",
        **extra,
    )
    if school is _SUBSCRIBED:
        school = subscribed_school() if role in (User.Role.STUDENT, User.Role.TEACHER) else None
    if school is not None:
        user.school = school
        user.school_status = User.SchoolStatus.APPROVED
        user.save(update_fields=["school", "school_status"])
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
    return Subject.objects.create(code="mathematics", name="Mathematics", name_fr="Mathématiques")


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
