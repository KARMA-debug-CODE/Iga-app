"""The assessments app's part of "Download my data" and "Delete my account" (apps/accounts/privacy.py)."""

from apps.core.exporting import iso, number

from .models import Answer, Attempt, Question, Quiz


def _answer(answer):
    return {
        "question": answer.question.prompt,
        "type": answer.question.type,
        "choices": [choice.text for choice in answer.selected_choices.all()],
        "text": answer.text_answer,
        "number": answer.numeric_answer,
        "checked_in_practice": answer.checked,
        "correct": answer.is_correct,
        "marks": number(answer.marks_awarded),
        "teacher_feedback": answer.teacher_feedback,
        "marked_at": iso(answer.marked_at),
    }


def export_for(user):
    attempts = (
        Attempt.objects.filter(user=user)
        .select_related("quiz")
        .prefetch_related("answers__question", "answers__selected_choices")
        .order_by("started_at")
    )
    return {
        "quiz_attempts": [
            {
                "quiz": attempt.quiz.title,
                "status": attempt.status,
                "started_at": iso(attempt.started_at),
                "submitted_at": iso(attempt.submitted_at),
                "score": number(attempt.score),
                "max_score": number(attempt.max_score),
                "answers": [_answer(answer) for answer in attempt.answers.all()],
            }
            for attempt in attempts
        ],
        # Teachers: the questions and quizzes they wrote (they stay on Iga after an erasure, without their name),
        # and how many answers they marked.
        "questions_written": [
            {"id": q.id, "prompt": q.prompt, "status": q.status, "created_at": iso(q.created_at)}
            for q in Question.objects.filter(author=user).order_by("created_at")
        ],
        "quizzes_written": [
            {"id": q.id, "title": q.title, "status": q.status} for q in Quiz.objects.filter(author=user).order_by("id")
        ],
        "answers_marked": Answer.objects.filter(marked_by=user).count(),
    }


def erase_for(user):
    # The student's attempts and answers go (Answer rows cascade). Questions and quizzes a teacher wrote, and the
    # marks they gave other students, stay with those students' work, pointing at the emptied account.
    Attempt.objects.filter(user=user).delete()
