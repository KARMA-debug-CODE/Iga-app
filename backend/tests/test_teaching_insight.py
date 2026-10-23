"""Teaching Packs: what a class gets wrong in a unit (apps/teaching/insight.py)."""

from datetime import timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.classroom.models import Enrollment
from apps.teaching.insight import question_stats, students_needing_help, unit_insight

from .conftest import add_mcq, make_user
from .teaching_factories import add_multi, class_with_students, mark_answer


def _answers(students, question, picks):
    """picks: one choice text per student; the correct choice gets full marks."""
    correct = question.choices.get(is_correct=True).text
    for student, pick in zip(students, picks, strict=True):
        mark_answer(student, question, question.marks if pick == correct else 0, choices=[pick])


def test_misconception_is_the_most_picked_wrong_option(teacher, subject, unit):
    c, students = class_with_students(teacher, subject, 6)
    q = add_mcq(subject, unit)
    _answers(students, q, ["3", "3", "3", "3", "5", "4"])
    m = unit_insight(c, unit)["misconceptions"][0]
    assert (m["wrong_choice"], m["share"], m["answered"], m["correct"]) == ("3", 0.67, 6, "4")
    assert m["question_id"] == q.id and m["prompt"] == "2 + 2?" and m["explanation"] == "Because."


def test_a_wrong_option_below_the_share_is_not_a_misconception(teacher, subject, unit):
    c, students = class_with_students(teacher, subject, 10)
    q = add_mcq(subject, unit)
    _answers(students, q, ["3", "3"] + ["4"] * 8)
    insight = unit_insight(c, unit)
    assert insight["data_enough"] is True and insight["misconceptions"] == []


def test_fewer_students_than_the_threshold_make_no_pattern(teacher, subject, unit):
    c, students = class_with_students(teacher, subject, 4)
    q = add_mcq(subject, unit)
    _answers(students, q, ["3"] * 4)
    insight = unit_insight(c, unit)
    assert insight["data_enough"] is False
    assert insight["misconceptions"] == [] and insight["hardest"] == []


def test_only_each_students_latest_answer_counts(teacher, subject, unit):
    c, students = class_with_students(teacher, subject, 5)
    q = add_mcq(subject, unit)
    earlier = timezone.now() - timedelta(days=2)
    for student in students:
        mark_answer(student, q, 0, choices=["3"], submitted_at=earlier)
        mark_answer(student, q, 1, choices=["4"])
    stat = question_stats(c, unit)[q.id]
    assert stat.answered == 5 and stat.correct == 5 and stat.most_picked_wrong() is None


def test_former_students_and_other_classes_are_ignored(teacher, other_teacher, subject, unit):
    c, students = class_with_students(teacher, subject, 5)
    _other, outsiders = class_with_students(other_teacher, subject, 3, prefix="outsider")
    q = add_mcq(subject, unit)
    _answers(students, q, ["4"] * 5)
    _answers(outsiders, q, ["3"] * 3)
    Enrollment.objects.filter(classroom=c, student=students[0]).update(active=False)
    stat = question_stats(c, unit)[q.id]
    assert stat.answered == 4 and stat.choice_counts.get(q.choices.get(text="3").id, 0) == 0


def test_answers_older_than_the_lookback_are_ignored(settings, teacher, subject, unit):
    settings.TEACHING_LOOKBACK_DAYS = 30
    c, students = class_with_students(teacher, subject, 5)
    q = add_mcq(subject, unit)
    for student in students:
        mark_answer(student, q, 0, choices=["3"], submitted_at=timezone.now() - timedelta(days=60))
    assert question_stats(c, unit) == {} or question_stats(c, unit)[q.id].answered == 0
    assert unit_insight(c, unit)["average"] is None


def test_partial_marks_on_multi_select_are_not_correct(teacher, subject, unit):
    c, students = class_with_students(teacher, subject, 5)
    q = add_multi(subject, unit)
    for student in students:
        mark_answer(student, q, 1, choices=["2", "4"])
    stat = question_stats(c, unit)[q.id]
    assert stat.correct == 0 and stat.correct_share == 0
    m = unit_insight(c, unit)["misconceptions"][0]
    assert (m["wrong_choice"], m["share"], m["correct"]) == ("4", 1.0, "2 / 3")


def test_hardest_lists_the_lowest_correct_share_first(teacher, subject, unit):
    c, students = class_with_students(teacher, subject, 5)
    easy, hard = add_mcq(subject, unit, "easy?"), add_mcq(subject, unit, "hard?")
    _answers(students, easy, ["4", "4", "4", "4", "3"])
    _answers(students, hard, ["4", "3", "3", "3", "3"])
    hardest = unit_insight(c, unit)["hardest"]
    assert [h["question_id"] for h in hardest] == [hard.id, easy.id]
    assert (hardest[0]["correct_share"], hardest[0]["answered"]) == (0.2, 5)


def test_other_units_compare_the_class(teacher, subject, unit):
    from apps.curriculum.models import Unit

    c, students = class_with_students(teacher, subject, 5)
    other = Unit.objects.create(subject=subject, grade="S2", number=2, title="Angles")
    _answers(students, add_mcq(subject, unit), ["3"] * 5)
    _answers(students, add_mcq(subject, other, "angle?"), ["4"] * 5)
    insight = unit_insight(c, unit)
    assert insight["average"] == 0.0
    assert insight["other_units"] == [{"label": "S2 Unit 2: Angles", "average": 100.0}]


def test_students_needing_help(teacher, subject, unit):
    c, (weak, few, strong, *_rest) = class_with_students(teacher, subject, 5)
    qs = [add_mcq(subject, unit, f"q{i}?") for i in range(5)]
    for q, marks in zip(qs[:3], (1, 0, 0), strict=True):
        mark_answer(weak, q, marks)
    for q in qs[:2]:
        mark_answer(few, q, 0)
    for q, marks in zip(qs, (1, 1, 1, 1, 0), strict=True):
        mark_answer(strong, q, marks)
    assert students_needing_help(c, unit) == [{"id": weak.id, "display_name": weak.display_name, "average": 33.3, "answered": 3}]


def test_insight_query_count_does_not_grow_with_attempts(teacher, subject, unit):
    def measure(count, prefix):
        c, students = class_with_students(teacher, subject, count, prefix=prefix)
        q1, q2 = add_mcq(subject, unit, f"{prefix}1?"), add_mcq(subject, unit, f"{prefix}2?")
        for student in students:
            mark_answer(student, q1, 0, choices=["3"])
            mark_answer(student, q2, 1, choices=["4"])
        with CaptureQueriesContext(connection) as queries:
            unit_insight(c, unit)
            students_needing_help(c, unit)
        return len(queries)

    assert measure(5, "small") == measure(50, "large")


def test_repeat_attempts_count_once_per_student_using_the_latest(teacher, subject, unit):
    # Two attempts per student on two quizzes: one answer per student, the latest.
    c, students = class_with_students(teacher, subject, 5)
    q = add_mcq(subject, unit)
    lone = make_user("lone")
    Enrollment.objects.create(classroom=c, student=lone)
    for student in [*students, lone]:
        mark_answer(student, q, 0, choices=["5"], submitted_at=timezone.now() - timedelta(hours=1))
        mark_answer(student, q, 0, choices=["3"])
    stat = question_stats(c, unit)[q.id]
    assert stat.answered == 6 and stat.most_picked_wrong()[0].text == "3"
