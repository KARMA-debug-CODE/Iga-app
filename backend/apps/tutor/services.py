"""AI study tutor built on the Claude API.

What the tutor is allowed to see is decided here, not by the model:
* a lesson's text, if the student can open that lesson;
* a quiz question and the student's own answer, but the correct answer,
  explanation and marking guide only once the student is allowed to see them
  (after submitting, or after checking a practice answer);
* nothing at all during a timed or exam-mode attempt that is still running.
"""

import logging

import anthropic
from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.assessments import services as assessment_services
from apps.assessments.models import Attempt, Question, Quiz
from apps.curriculum.views import visible_lessons

from .models import TutorExchange

log = logging.getLogger(__name__)

LANGUAGE_NAMES = {"en": "English", "fr": "French"}
MAX_HISTORY_MESSAGES = 10
MAX_MESSAGE_CHARS = 2000

SYSTEM_PROMPT = """You are Iga Tutor, a patient and encouraging study helper for secondary-school students in Rwanda (Senior 1 to Senior 6) following the Rwandan competence-based curriculum.

How to help:
- Explain ideas step by step at the level of the student's grade, using simple language and short paragraphs.
- Prefer examples from everyday life in Rwanda (FRW prices, moto taxis, farming, local places).
- Use Markdown. Write maths with LaTeX between $...$ (inline) or $$...$$ (display); it is rendered with KaTeX.
- Keep replies under about 250 words unless the student asks for more. End with a short question that checks understanding when it helps.
- If you are not sure about a fact, say so and suggest checking the textbook or asking the teacher.

Honesty in assessments:
- When the context says the student is still answering a question, never state or confirm the final answer. Give a hint, point to the relevant idea, or ask a guiding question instead.
- When the context includes the correct answer and the student's answer, explain why the correct answer is right and, kindly, where the student's reasoning went wrong.

Safety:
- Stay on schoolwork and study skills. Politely decline unrelated requests.
- Never ask for personal information (full name, phone number, address, school, passwords) and tell the student not to share it.
- If a student says they are unsafe, being hurt, or thinking of hurting themselves, respond with care, encourage them to talk to a trusted adult or teacher straight away, and mention that in Rwanda they can call the free child helpline 116."""

REFUSAL_REPLY = "I can't help with that one. Try asking about your lesson or a practice question, or ask your teacher."
REFUSAL_REPLIES = {
    "en": REFUSAL_REPLY,
    "fr": "Je ne peux pas t'aider sur ce point. Pose une question sur ta leçon ou un exercice, ou demande à ton enseignant.",
}
OUT_OF_SPACE = {
    "en": "*(I ran out of space — ask me to continue.)*",
    "fr": "*(Je n'ai plus de place — demande-moi de continuer.)*",
}


def reply_language(user, lang=None):
    return lang if lang in LANGUAGE_NAMES else (user.preferred_language if user.preferred_language in LANGUAGE_NAMES else "en")


def tutor_enabled():
    return bool(settings.TUTOR_ENABLED)


def get_client():
    """The Anthropic client. Credentials come from the environment (ANTHROPIC_API_KEY or an `ant auth` profile)."""
    return anthropic.Anthropic(timeout=settings.TUTOR_TIMEOUT_SECONDS, max_retries=2)


def clean_history(history):
    """Validate prior turns sent by the browser: alternating user/assistant text, oldest first."""
    if not history:
        return []
    if not isinstance(history, list):
        raise ValidationError({"history": _("Must be a list of messages.")})
    history = history[-MAX_HISTORY_MESSAGES:]
    if history and history[0].get("role") != "user":
        history = history[1:]
    cleaned = []
    for i, item in enumerate(history):
        role = item.get("role") if isinstance(item, dict) else None
        content = item.get("content") if isinstance(item, dict) else None
        expected = "user" if i % 2 == 0 else "assistant"
        if role != expected or not isinstance(content, str) or not content.strip():
            raise ValidationError({"history": _("Messages must alternate between the student and the tutor.")})
        cleaned.append({"role": role, "content": content[:4000]})
    if cleaned and cleaned[-1]["role"] != "assistant":
        raise ValidationError({"history": _("The history must end with a tutor reply.")})
    return cleaned


def _question_text(attempt, question):
    lines = [f"Question ({question.get_type_display()}, {question.marks} marks):", question.prompt]
    choices = assessment_services.ordered_choices(attempt, question)
    if choices:
        lines.append("Options:")
        lines += [f"- {c.text}" for c in choices]
    return "\n".join(lines)


def _student_answer_text(question, answer):
    if answer is None:
        return "The student has not answered yet."
    if question.type in Question.CHOICE_TYPES:
        picked = [c.text for c in answer.selected_choices.all()]
        return "Student's answer: " + (", ".join(picked) if picked else "(no option chosen)")
    if question.type == Question.Type.NUMERIC:
        return f"Student's answer: {answer.numeric_answer if answer.numeric_answer is not None else '(blank)'}"
    return "Student's answer:\n" + (answer.text_answer or "(blank)")


def _solution_text(question, answer):
    correct = [c.text for c in question.choices.all() if c.is_correct]
    parts = []
    if correct:
        parts.append("Correct option(s): " + ", ".join(correct))
    if question.type == Question.Type.NUMERIC and question.numeric_answer is not None:
        parts.append(f"Correct answer: {question.numeric_answer} (allowed difference ±{question.numeric_tolerance})")
    if question.type == Question.Type.SHORT and question.accepted_answers:
        parts.append("Accepted answers: " + ", ".join(question.accepted_answers))
    if question.explanation:
        parts.append("Explanation from the question author:\n" + question.explanation)
    if question.marking_guide:
        parts.append("Marking guide:\n" + question.marking_guide)
    if answer is not None and answer.marks_awarded is not None:
        parts.append(f"Marks awarded: {answer.marks_awarded} / {question.marks}")
    if answer is not None and answer.teacher_feedback:
        parts.append("Teacher's feedback: " + answer.teacher_feedback)
    return "\n".join(parts)


def build_context(user, lesson_slug=None, attempt_id=None, question_id=None, lang=None):
    """Return (context_text, lesson, attempt, question) for what the student is looking at.

    `lang` is the language the student is reading in (defaults to their saved preference)."""
    code = reply_language(user, lang)
    lang = LANGUAGE_NAMES[code]
    grade = user.grade or "secondary school"
    sections = [
        f"The student is in {grade}. Reply in {lang} unless the student writes in another language; then reply in theirs."
    ]
    lesson = attempt = question = None

    if lesson_slug:
        lesson = visible_lessons(user).select_related("unit__subject").filter(slug=lesson_slug).first()
        if lesson is None:
            raise NotFound(_("Lesson not found."))
        unit = lesson.unit
        # Quote the lesson in the language the student is reading, when it has been translated.
        translation = lesson.translations.filter(language=code).first() if code != "en" else None
        title, body = (translation.title, translation.body) if translation else (lesson.title, lesson.body)
        sections.append(
            f"The student is studying this lesson ({unit.subject.name}, {unit.grade}, unit {unit.number}: {unit.title}).\n"
            f'<lesson title="{title}">\n{body}\n</lesson>'
        )

    if attempt_id:
        attempt = Attempt.objects.select_related("quiz", "quiz__subject").filter(pk=attempt_id, user=user).first()
        if attempt is None:
            raise NotFound(_("Attempt not found."))
        assessment_services.finalize_if_expired(attempt)
        in_progress = attempt.status == Attempt.Status.IN_PROGRESS
        if in_progress and (attempt.deadline or attempt.quiz.feedback_mode == Quiz.FeedbackMode.AFTER_SUBMIT):
            raise PermissionDenied(_("The tutor is switched off during exams and timed tests. Good luck!"))
        if question_id:
            try:
                question_id = int(question_id)
            except (TypeError, ValueError):
                raise ValidationError({"question": _("Unknown question.")})
            if question_id not in attempt.question_order:
                raise NotFound(_("That question is not part of this attempt."))
            question = Question.objects.prefetch_related("choices").get(pk=question_id)
            answer = attempt.answers.filter(question=question).prefetch_related("selected_choices").first()
            block = [
                f"Quiz: {attempt.quiz.title} ({attempt.quiz.subject.name}, {attempt.quiz.grade}).",
                _question_text(attempt, question),
            ]
            if assessment_services.can_see_solutions(attempt, answer):
                block.append(_student_answer_text(question, answer))
                block.append(_solution_text(question, answer))
                block.append("The student has finished this question and may see the answer.")
            else:
                block.append(_student_answer_text(question, answer))
                block.append(
                    "The student is STILL ANSWERING this practice question. Do not reveal or confirm the answer; give hints only."
                )
            sections.append("<quiz_question>\n" + "\n\n".join(block) + "\n</quiz_question>")
        else:
            sections.append(f'The student is working on the quiz "{attempt.quiz.title}".')

    return "\n\n".join(sections), lesson, attempt, question


def ask(user, message, history=None, lesson_slug=None, attempt_id=None, question_id=None, lang=None):
    message = (message or "").strip()
    if not message:
        raise ValidationError({"message": _("Write a question for the tutor.")})
    if len(message) > MAX_MESSAGE_CHARS:
        raise ValidationError({"message": _("Please keep questions under %(n)s characters.") % {"n": MAX_MESSAGE_CHARS}})
    history = clean_history(history)
    context, lesson, attempt, question = build_context(user, lesson_slug, attempt_id, question_id, lang)
    code = reply_language(user, lang)

    response = get_client().beta.messages.create(
        model=settings.TUTOR_MODEL,
        max_tokens=settings.TUTOR_MAX_TOKENS,
        # If a safety classifier declines, the API retries on Anthropic's recommended fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": settings.TUTOR_EFFORT},
        system=[{"type": "text", "text": SYSTEM_PROMPT}, {"type": "text", "text": context}],
        messages=[*history, {"role": "user", "content": message}],
    )

    if response.stop_reason == "refusal":
        reply = REFUSAL_REPLIES[code]
    else:
        reply = "\n\n".join(block.text for block in response.content if block.type == "text").strip()
        if response.stop_reason == "max_tokens":
            reply += "\n\n" + OUT_OF_SPACE[code]
        if not reply:
            reply = REFUSAL_REPLIES[code]

    usage = getattr(response, "usage", None)
    TutorExchange.objects.create(
        user=user,
        lesson=lesson,
        attempt=attempt,
        question=question,
        message=message,
        reply=reply,
        model=getattr(response, "model", "") or "",
        stop_reason=response.stop_reason or "",
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
    )
    return reply
