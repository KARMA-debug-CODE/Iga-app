"""Item analysis for teachers: how a class did on a quiz, question by question."""

from decimal import Decimal
from statistics import median

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.classroom.models import Classroom, Enrollment

from .models import Answer, Attempt, Question


def _students_for(user, classroom_id):
    """Students whose results this teacher may analyse, and the class (if one was chosen)."""
    if classroom_id:
        classroom = get_object_or_404(Classroom, pk=classroom_id)
        if classroom.teacher_id != user.id and not user.is_platform_admin:
            raise PermissionDenied("That is not your class.")
        return set(classroom.enrollments.values_list("student_id", flat=True)), classroom
    if user.is_platform_admin:
        return None, None  # everyone
    current = Enrollment.objects.filter(classroom__teacher=user, classroom__archived=False)
    return set(current.values_list("student_id", flat=True)), None


def quiz_analytics(quiz, user, classroom_id=None):
    student_ids, classroom = _students_for(user, classroom_id)
    finished = Attempt.objects.filter(quiz=quiz).exclude(status=Attempt.Status.IN_PROGRESS).order_by("submitted_at", "id")
    if student_ids is not None:
        finished = finished.filter(user_id__in=student_ids)

    # Each student's FIRST finished attempt: retries after seeing answers would hide misconceptions.
    first = {}
    for attempt in finished:
        first.setdefault(attempt.user_id, attempt)
    attempts = list(first.values())

    links = list(quiz.quiz_questions.select_related("question").prefetch_related("question__choices").order_by("order", "id"))
    questions = [link.question for link in links]
    answers = Answer.objects.filter(attempt__in=attempts).prefetch_related("selected_choices")
    by_attempt = {}
    for answer in answers:
        by_attempt.setdefault(answer.attempt_id, {})[answer.question_id] = answer

    percentages = [a.percentage for a in attempts if a.percentage is not None]
    histogram = [0] * 10
    for pct in percentages:
        histogram[min(9, int(pct // 10))] += 1

    # Upper and lower 27% by total score, for the discrimination index.
    ranked = sorted((a for a in attempts if a.score is not None), key=lambda a: float(a.score))
    k = max(1, round(len(ranked) * 0.27)) if len(ranked) >= 4 else 0
    lower, upper = (ranked[:k], ranked[-k:]) if k else ([], [])

    def fraction(attempt, question):
        answer = by_attempt.get(attempt.id, {}).get(question.id)
        if answer is None or answer.marks_awarded is None or not question.marks:
            return Decimal("0")
        return Decimal(answer.marks_awarded) / Decimal(question.marks)

    rows = []
    for number, question in enumerate(questions, start=1):
        marked = []
        pending = 0
        choice_counts = {c.id: 0 for c in question.choices.all()}
        for attempt in attempts:
            answer = by_attempt.get(attempt.id, {}).get(question.id)
            if answer is None:
                continue
            if answer.marks_awarded is None:
                pending += 1
            else:
                marked.append(answer)
            for choice in answer.selected_choices.all():
                if choice.id in choice_counts:
                    choice_counts[choice.id] += 1
        possible = Decimal(question.marks) * len(marked)
        got = sum((Decimal(a.marks_awarded) for a in marked), Decimal("0"))
        discrimination = None
        if k:
            discrimination = round(
                float(sum(fraction(a, question) for a in upper) / k - sum(fraction(a, question) for a in lower) / k), 2
            )
        rows.append(
            {
                "id": question.id,
                "number": number,
                "type": question.type,
                "prompt": question.prompt,
                "marks": question.marks,
                "marked": len(marked),
                "pending_marking": pending,
                "average_pct": round(float(got / possible * 100), 1) if possible else None,
                "full_marks_pct": round(sum(1 for a in marked if a.is_correct) / len(marked) * 100, 1) if marked else None,
                "discrimination": discrimination,
                "choices": [
                    {"id": c.id, "text": c.text, "is_correct": c.is_correct, "count": choice_counts[c.id]}
                    for c in question.choices.all()
                ]
                if question.type in Question.CHOICE_TYPES
                else [],
            }
        )

    return {
        "quiz": {"id": quiz.id, "title": quiz.title, "subject": quiz.subject.name, "grade": quiz.grade},
        "classroom": {"id": classroom.id, "name": classroom.name, "students": len(student_ids)} if classroom else None,
        "students_attempted": len(attempts),
        "average_pct": round(sum(percentages) / len(percentages), 1) if percentages else None,
        "median_pct": round(median(percentages), 1) if percentages else None,
        "histogram": [{"from": i * 10, "to": 100 if i == 9 else i * 10 + 9, "count": n} for i, n in enumerate(histogram)],
        "questions": rows,
        "hardest": [
            r["number"] for r in sorted((r for r in rows if r["average_pct"] is not None), key=lambda r: r["average_pct"])[:3]
        ],
    }
