"""Attempt lifecycle and auto-marking.

Rules that keep tests fair:
* correct answers never leave the server until the student is allowed to see them;
* question and option order is shuffled per attempt (fixed at start, survives a refresh);
* timed attempts are closed by the server, not the browser clock;
* in practice mode, an answer is locked once the student has checked it.
"""

import random
import re
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.constants import ContentStatus
from apps.gamification import services as gamification

from .models import Answer, Attempt, Question, Quiz

_rng = random.SystemRandom()
TWO_PLACES = Decimal("0.01")


def visible_quizzes(user):
    """Quizzes this user may open."""
    qs = Quiz.objects.all()
    if user.is_platform_admin:
        return qs
    published = Q(status=ContentStatus.PUBLISHED)
    if user.can_teach:
        return qs.filter(published | Q(author=user))
    # Use a subquery rather than a join so callers can safely aggregate over the result.
    assigned_ids = Quiz.objects.filter(
        assignments__classroom__enrollments__student=user, assignments__classroom__archived=False
    ).values("id")
    return qs.filter(published | Q(id__in=assigned_ids)).exclude(status=ContentStatus.ARCHIVED)


def library_questions_q(prefix=""):
    """Questions from the Iga library (imported or written by platform admins): premium material.
    Questions written by teachers are their school's own work."""
    p = prefix
    return Q(**{f"{p}author__isnull": True}) | Q(**{f"{p}author__role": "admin"}) | Q(**{f"{p}author__is_superuser": True})


def quiz_is_teacher_material(quiz):
    """A teacher's quiz is free only if none of its questions come from the premium library,
    so library questions can't be repackaged into a free quiz."""
    return not quiz.quiz_questions.filter(library_questions_q("question__")).exists()


def _q(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def normalise_text(value):
    value = re.sub(r"\s+", " ", (value or "").strip().lower())
    return value.rstrip(".")


# --- Starting ---------------------------------------------------------------


def start_attempt(user, quiz, assignment=None):
    """Return the open attempt for this quiz, or start a new one.

    Expired attempts are closed first, in their own transaction, so a refusal below
    (no attempts left) doesn't undo the automatic submission.
    """
    for stale in Attempt.objects.filter(user=user, quiz=quiz, status=Attempt.Status.IN_PROGRESS):
        finalize_if_expired(stale)

    with transaction.atomic():
        # Serialise starts per user: a double-tap can't create two attempts or exceed max_attempts.
        type(user).objects.select_for_update().only("pk").get(pk=user.pk)
        existing = Attempt.objects.filter(user=user, quiz=quiz, status=Attempt.Status.IN_PROGRESS).first()
        if existing:
            if assignment is not None and existing.assignment_id is None:
                existing.assignment = assignment
                existing.save(update_fields=["assignment"])
            return existing
        return _create_attempt(user, quiz, assignment)


def _create_attempt(user, quiz, assignment):
    if quiz.max_attempts:
        used = Attempt.objects.filter(user=user, quiz=quiz).count()
        if used >= quiz.max_attempts:
            raise PermissionDenied(_("You have used all your attempts for this quiz."))

    links = list(quiz.quiz_questions.select_related("question").prefetch_related("question__choices"))
    if not links:
        raise ValidationError(_("This quiz has no questions yet."))

    questions = [link.question for link in links]
    if quiz.shuffle_questions:
        _rng.shuffle(questions)

    choice_order = {}
    for question in questions:
        if question.type in Question.CHOICE_TYPES:
            ids = [c.id for c in question.choices.all()]
            if quiz.shuffle_choices and question.type != Question.Type.TRUE_FALSE:
                _rng.shuffle(ids)
            choice_order[str(question.id)] = ids

    now = timezone.now()
    return Attempt.objects.create(
        user=user,
        quiz=quiz,
        assignment=assignment,
        started_at=now,
        deadline=now + timedelta(minutes=quiz.time_limit_minutes) if quiz.time_limit_minutes else None,
        question_order=[q.id for q in questions],
        choice_order=choice_order,
        max_score=sum((q.marks for q in questions), Decimal("0")),
    )


# --- Answering --------------------------------------------------------------


def _ensure_open(attempt):
    """Must run outside a transaction so an automatic submit isn't rolled back by the error."""
    if attempt.status != Attempt.Status.IN_PROGRESS:
        raise ValidationError(_("This attempt has already been submitted."))
    if not attempt.accepts_submission():
        submit_attempt(attempt)
        raise ValidationError(_("Time is up — your attempt was submitted automatically."))


def _question_in_attempt(attempt, question_id):
    try:
        question_id = int(question_id)
    except (TypeError, ValueError):
        raise ValidationError(_("Unknown question."))
    if question_id not in attempt.question_order:
        raise ValidationError(_("That question is not part of this attempt."))
    return Question.objects.prefetch_related("choices").get(pk=question_id)


def _lock_open(attempt):
    """Lock the attempt row so a save can't land after (or during) the submit that scored it."""
    locked = Attempt.objects.select_for_update().get(pk=attempt.pk)
    if locked.status != Attempt.Status.IN_PROGRESS:
        raise ValidationError(_("This attempt has already been submitted."))
    return locked


def save_answer(attempt, question_id, choice_ids=None, text="", numeric=None):
    _ensure_open(attempt)
    with transaction.atomic():
        return _save_answer(_lock_open(attempt), question_id, choice_ids, text, numeric)


def _save_answer(attempt, question_id, choice_ids, text, numeric):
    question = _question_in_attempt(attempt, question_id)
    answer, _created = Answer.objects.get_or_create(attempt=attempt, question=question)
    if answer.checked:
        raise ValidationError(_("You already checked this answer, so it can't be changed."))

    if question.type in Question.CHOICE_TYPES:
        try:
            choice_ids = [int(c) for c in (choice_ids or [])]
        except (TypeError, ValueError):
            raise ValidationError(_("Invalid option selected."))
        valid = set(question.choices.values_list("id", flat=True))
        if not set(choice_ids) <= valid:
            raise ValidationError(_("Invalid option selected."))
        if question.type != Question.Type.MULTI and len(choice_ids) > 1:
            raise ValidationError(_("Choose only one option."))
        answer.save()
        answer.selected_choices.set(choice_ids)
    elif question.type == Question.Type.NUMERIC:
        if numeric in (None, ""):
            answer.numeric_answer = None
        else:
            try:
                answer.numeric_answer = float(numeric)
            except (TypeError, ValueError):
                raise ValidationError(_("Enter a number."))
        answer.save()
    else:
        answer.text_answer = (text or "")[:10000]
        answer.save()
    return answer


def score_answer(answer):
    """Return (is_correct, marks). Both are None when a teacher must mark it."""
    question = answer.question
    full = Decimal(question.marks)

    if question.type in Question.CHOICE_TYPES:
        selected = set(answer.selected_choices.values_list("id", flat=True))
        correct = set(question.choices.filter(is_correct=True).values_list("id", flat=True))
        if question.type == Question.Type.MULTI and correct:
            hits = len(selected & correct)
            wrong = len(selected - correct)
            fraction = max(0, hits - wrong) / len(correct)
            return selected == correct, _q(full * Decimal(str(fraction)))
        is_correct = bool(selected) and selected == correct
        return is_correct, full if is_correct else Decimal("0")

    if question.type == Question.Type.NUMERIC:
        if answer.numeric_answer is None or question.numeric_answer is None:
            return False, Decimal("0")
        expected = question.numeric_answer
        # Float noise grows with magnitude (e.g. 6.02e23), so the allowance is relative.
        allowance = question.numeric_tolerance + 1e-9 * max(1.0, abs(expected))
        is_correct = abs(answer.numeric_answer - expected) <= allowance
        return is_correct, full if is_correct else Decimal("0")

    if question.type == Question.Type.SHORT and question.accepted_answers:
        given = normalise_text(answer.text_answer)
        accepted = {normalise_text(a) for a in question.accepted_answers}
        is_correct = bool(given) and given in accepted
        return is_correct, full if is_correct else Decimal("0")

    return None, None


def check_answer(attempt, question_id):
    """Practice mode: mark one answer now and lock it."""
    if attempt.quiz.feedback_mode != Quiz.FeedbackMode.IMMEDIATE:
        raise PermissionDenied(_("Answers are revealed after you submit in exam mode."))
    _ensure_open(attempt)
    with transaction.atomic():
        attempt = _lock_open(attempt)
        question = _question_in_attempt(attempt, question_id)
        if question.needs_manual_marking:
            raise ValidationError(_("Your teacher will mark this answer."))
        answer, _created = Answer.objects.select_for_update().get_or_create(attempt=attempt, question=question)
        if not answer.checked:
            answer.is_correct, answer.marks_awarded = score_answer(answer)
            answer.checked = True
            answer.save()
        return answer


# --- Submitting & marking -----------------------------------------------------


def _recalculate(attempt):
    answers = list(attempt.answers.all())
    attempt.score = _q(sum((a.marks_awarded or Decimal("0") for a in answers), Decimal("0")))
    pending = any(a.marks_awarded is None for a in answers)
    attempt.status = Attempt.Status.NEEDS_MARKING if pending else Attempt.Status.MARKED
    attempt.save(update_fields=["score", "status"])
    if attempt.status == Attempt.Status.MARKED:
        gamification.on_attempt_marked(attempt)


@transaction.atomic
def submit_attempt(attempt):
    attempt = Attempt.objects.select_for_update().get(pk=attempt.pk)
    if attempt.status != Attempt.Status.IN_PROGRESS:
        return attempt
    questions = Question.objects.in_bulk(attempt.question_order)
    for question_id in attempt.question_order:
        if question_id not in questions:  # deleted after the attempt started
            continue
        answer, _created = Answer.objects.get_or_create(attempt=attempt, question=questions[question_id])
        if not answer.checked:
            answer.is_correct, answer.marks_awarded = score_answer(answer)
            if answer.marks_awarded is None and not answer.text_answer.strip():
                # A blank written answer scores zero; don't send it to the teacher's queue.
                answer.is_correct, answer.marks_awarded = False, Decimal("0")
            answer.save(update_fields=["is_correct", "marks_awarded"])
    now = timezone.now()
    attempt.submitted_at = min(now, attempt.deadline) if attempt.deadline else now
    attempt.save(update_fields=["submitted_at"])
    _recalculate(attempt)
    return attempt


def finalize_if_expired(attempt):
    """Close an attempt whose time ran out. Returns True if it was closed."""
    if attempt.status == Attempt.Status.IN_PROGRESS and not attempt.accepts_submission():
        submit_attempt(attempt)
        attempt.refresh_from_db()
        return True
    return False


@transaction.atomic
def mark_answer(answer, marks, feedback, teacher):
    question = answer.question
    marks = _q(marks)
    if marks < 0 or marks > Decimal(question.marks):
        raise ValidationError(_("Marks must be between 0 and %(max)s.") % {"max": question.marks})
    # Lock the attempt so two teachers marking different answers both count in the total.
    answer.attempt = Attempt.objects.select_for_update().get(pk=answer.attempt_id)
    if answer.attempt.status == Attempt.Status.IN_PROGRESS:
        raise ValidationError(_("The student hasn't submitted yet."))
    answer.marks_awarded = marks
    answer.is_correct = marks == Decimal(question.marks)
    answer.teacher_feedback = feedback or ""
    answer.marked_by = teacher
    answer.marked_at = timezone.now()
    answer.save()
    _recalculate(answer.attempt)
    return answer


def manual_questions_q(prefix=""):
    """Questions a person marks: essays, and short answers with no accepted-answer list."""
    p = prefix
    return Q(**{f"{p}type": Question.Type.ESSAY}) | (
        Q(**{f"{p}type": Question.Type.SHORT}) & (Q(**{f"{p}accepted_answers": []}) | Q(**{f"{p}accepted_answers__isnull": True}))
    )


def markable_answers(user):
    """Submitted written answers this teacher may mark.

    A teacher marks work for their own (current) classes: answers to an assignment they set,
    or self-practice by one of their students in that class's subject. Auto-marked questions
    are never re-marked by hand.
    """
    qs = Answer.objects.exclude(attempt__status=Attempt.Status.IN_PROGRESS).filter(manual_questions_q("question__"))
    if user.is_platform_admin:
        return qs
    from apps.classroom.models import Enrollment

    teaches_this = Enrollment.objects.filter(
        classroom__teacher=user,
        classroom__archived=False,
        student=OuterRef("attempt__user"),
    ).filter(Q(classroom__subject__isnull=True) | Q(classroom__subject=OuterRef("attempt__quiz__subject")))
    own_assignment = Q(attempt__assignment__classroom__teacher=user, attempt__assignment__classroom__archived=False)
    return qs.filter(own_assignment | Q(Exists(teaches_this)))


def can_see_solutions(attempt, answer=None):
    if attempt.status != Attempt.Status.IN_PROGRESS:
        return True
    return bool(answer and answer.checked)


def correct_choice_ids(question):
    return [c.id for c in question.choices.all() if c.is_correct]


def ordered_choices(attempt, question):
    by_id = {c.id: c for c in question.choices.all()}
    order = attempt.choice_order.get(str(question.id))
    if not order:
        return list(by_id.values())
    choices = [by_id[i] for i in order if i in by_id]
    # Options added after the attempt started go at the end.
    choices += [c for i, c in by_id.items() if i not in order]
    return choices
