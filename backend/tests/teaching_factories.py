"""Test helpers for Teaching Packs: classes with students and marked answers."""

from decimal import Decimal

from django.utils import timezone

from apps.assessments.models import Answer, Attempt, Choice, Question
from apps.classroom.models import Classroom, Enrollment

from .conftest import make_quiz, make_user


def class_with_students(teacher, subject, count, prefix="pupil", grade="S2"):
    classroom = Classroom.objects.create(name=f"{grade} {prefix}", subject=subject, grade=grade, teacher=teacher)
    students = [make_user(f"{prefix}{i}") for i in range(count)]
    for student in students:
        Enrollment.objects.create(classroom=classroom, student=student)
    return classroom, students


def add_multi(subject, unit, prompt="Pick the primes", correct=("2", "3"), wrong=("4",), marks=2):
    q = Question.objects.create(
        subject=subject, grade=unit.grade, unit=unit, type=Question.Type.MULTI, prompt=prompt, marks=marks, explanation="Primes."
    )
    for text in correct:
        Choice.objects.create(question=q, text=text, is_correct=True)
    for text in wrong:
        Choice.objects.create(question=q, text=text, is_correct=False)
    return q


def mark_answer(student, question, marks, choices=(), submitted_at=None, quiz=None):
    """A marked attempt holding one marked answer by `student` to `question`, ticking the choices named in `choices`."""
    quiz = quiz or make_quiz(question.subject, question.unit, [question])
    attempt = Attempt.objects.create(
        user=student, quiz=quiz, status=Attempt.Status.MARKED, submitted_at=submitted_at or timezone.now()
    )
    answer = Answer.objects.create(
        attempt=attempt, question=question, marks_awarded=Decimal(marks), is_correct=Decimal(marks) == question.marks
    )
    if choices:
        answer.selected_choices.set(question.choices.filter(text__in=choices))
    return answer
