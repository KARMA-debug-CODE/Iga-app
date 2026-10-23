"""The class unit scores shared by the gradebook and Teaching Packs (apps/classroom/analytics.py)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.assessments.models import Answer, Attempt
from apps.classroom.analytics import class_unit_scores
from apps.classroom.models import Classroom, Enrollment
from apps.curriculum.models import Unit

from .conftest import add_mcq, make_quiz, make_user


def _mark(student, quiz, question, marks, submitted_at=None):
    attempt = Attempt.objects.create(
        user=student, quiz=quiz, status=Attempt.Status.MARKED, submitted_at=submitted_at or timezone.now()
    )
    Answer.objects.create(attempt=attempt, question=question, marks_awarded=Decimal(marks))
    return attempt


@pytest.fixture
def scored(db, teacher, student, subject, unit):
    """Unit A scores 1/4 marks, unit B scores 3/4 marks, all by one enrolled student."""
    unit_b = Unit.objects.create(subject=subject, grade="S2", number=2, title="Angles")
    classroom = Classroom.objects.create(name="S2 A", subject=subject, grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=student)
    a1, a2 = add_mcq(subject, unit, "a1?", marks=2), add_mcq(subject, unit, "a2?", marks=2)
    b1, b2 = add_mcq(subject, unit_b, "b1?", marks=2), add_mcq(subject, unit_b, "b2?", marks=2)
    quiz_a, quiz_b = make_quiz(subject, unit, [a1, a2]), make_quiz(subject, unit_b, [b1, b2])
    _mark(student, quiz_a, a1, 1)
    _mark(student, quiz_a, a2, 0)
    _mark(student, quiz_b, b1, 2)
    _mark(student, quiz_b, b2, 1)
    return {"classroom": classroom, "unit_a": unit, "unit_b": unit_b, "quiz_a": quiz_a, "a1": a1}


def test_report_weak_units_are_unchanged_and_carry_the_unit_id(client_for, teacher, scored):
    unit_a, unit_b = scored["unit_a"], scored["unit_b"]
    report = client_for(teacher).get(f"/api/classes/{scored['classroom'].id}/report/").json()
    assert report["weak_units"] == [
        {
            "unit": f"{unit_a.grade} Unit {unit_a.number}: {unit_a.title}",
            "average": 25.0,
            "unit_id": unit_a.id,
            "of_class_grade": True,
        },
        {
            "unit": f"{unit_b.grade} Unit {unit_b.number}: {unit_b.title}",
            "average": 75.0,
            "unit_id": unit_b.id,
            "of_class_grade": True,
        },
    ]


def test_report_marks_weak_units_from_another_grade(client_for, teacher, student, subject, scored):
    # S2 students revising an S1 unit: the unit is listed, but it is not one of the class's own (no pack for it).
    revision = Unit.objects.create(subject=subject, grade="S1", number=9, title="Revision")
    question = add_mcq(subject, revision, "Old?")
    _mark(student, make_quiz(subject, revision, [question]), question, 0)
    rows = client_for(teacher).get(f"/api/classes/{scored['classroom'].id}/report/").json()["weak_units"]
    assert {row["unit_id"]: row["of_class_grade"] for row in rows} == {
        revision.id: False,
        scored["unit_a"].id: True,
        scored["unit_b"].id: True,
    }


def test_class_unit_scores_are_weakest_first(student, scored):
    scores = class_unit_scores(scored["classroom"], [student])
    assert [s.unit for s in scores] == [scored["unit_a"], scored["unit_b"]]
    assert [(s.got, s.possible, s.average) for s in scores] == [(1.0, 4.0, 25.0), (3.0, 4.0, 75.0)]


def test_class_unit_scores_respect_since(student, scored):
    # An old, perfect attempt on unit A must not lift its score when `since` is later.
    _mark(student, scored["quiz_a"], scored["a1"], 2, submitted_at=timezone.now() - timedelta(days=400))
    recent = class_unit_scores(scored["classroom"], [student], since=timezone.now() - timedelta(days=30))
    assert recent[0].unit == scored["unit_a"] and recent[0].average == 25.0
    everything = class_unit_scores(scored["classroom"], [student])
    assert everything[0].unit == scored["unit_a"] and everything[0].average == 50.0


def test_class_unit_scores_count_only_the_given_students(student, scored):
    outsider = make_user("outsider")
    _mark(outsider, scored["quiz_a"], scored["a1"], 2)
    scores = class_unit_scores(scored["classroom"], [student])
    assert scores[0].average == 25.0
    assert class_unit_scores(scored["classroom"], []) == []
