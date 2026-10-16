"""Santa, Iga's learning assistant: a study helper whose model runs on the school's own server.

What Santa may see is decided here, not by the model:
* passages from the lessons this student may read, and the lesson they have open;
* a quiz question and the student's own answer, but the correct answer, explanation and marking guide only
  once the student is allowed to see them (after submitting, or after checking a practice answer);
* nothing at all while the student has a timed or exam-mode attempt still running, whichever page they ask from.

The model (an open model on llama.cpp, see llm.py) gets a short system prompt that never changes, so the model
server can reuse its prompt cache; everything about this question goes in the student's turn. The model may
call a calculator (calculator.py) for exact arithmetic. When the model is not installed, still loading, busy
or not answering, Santa still helps: it answers with the best matching passages from the lessons.
"""

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache
from django.utils import translation
from django.utils.translation import gettext as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.assessments import services as assessment_services
from apps.assessments.models import Attempt, Question, Quiz
from apps.curriculum.models import Subject
from apps.curriculum.views import visible_lessons
from apps.schools import access

from . import calculator, llm, retrieval
from .models import TutorExchange

log = logging.getLogger(__name__)

LANGUAGE_NAMES = {"en": "English", "fr": "French"}
MAX_MESSAGE_CHARS = 2000
# Each of the model server's slots holds about 4,000 tokens (llama-server -c 16384 -np 4), shared by the
# system prompt, the history, this question with its lesson passages, and the answer. These limits keep a
# request near 3,000 tokens, in English and in French.
MAX_HISTORY_MESSAGES = 10
HISTORY_CHARS = 3000
HISTORY_MESSAGE_CHARS = 1500
QUESTION_CHARS = 2500
PASSAGE_CHARS = 2800
OPEN_LESSON_CHARS = 2000
# The history and the student's turn together (about 2,800 tokens at 3 characters a token, which French
# and maths need): lesson passages get less room, and old turns are dropped, when a question is long.
TURN_CHARS = 8400
MIN_PASSAGE_CHARS = 800
MAX_TOOL_ROUNDS = 3
FALLBACK_PASSAGES = 3
FALLBACK_EXCERPT_CHARS = 700

# Short and the same for every request, so llama.cpp keeps it in its prompt cache.
SYSTEM_PROMPT = """You are Santa, Iga's learning assistant: a patient, encouraging study helper for secondary-school students in Rwanda (Senior 1 to Senior 6) following the Rwandan competence-based curriculum.

How to help:
- Explain ideas step by step at the student's grade, in simple words and short paragraphs.
- Prefer examples from everyday life in Rwanda (FRW prices, moto taxis, farming, local places).
- The message may include passages from the student's Iga lessons. Base your answer on them when they are relevant and say which lesson helps. If you are not sure of a fact, say so and suggest the textbook or the teacher.
- For arithmetic, use the calculate tool when it is available instead of working it out in your head.
- Use Markdown. Write maths in LaTeX between $...$ (inline) or $$...$$ (display).
- Keep answers under about 200 words unless the student asks for more. When it helps, end with one short question that checks understanding.
- Reply in the language the context asks for (English or French), unless the student writes in another language.

Homework and quizzes:
- Help the student find answers themselves with hints, steps and guiding questions; don't just hand over the final answer to homework.
- If the context says the student is STILL ANSWERING a quiz question, never state or confirm the answer. Give a hint or a guiding question instead.
- If the context gives the correct answer, explain why it is right and, kindly, where the student's reasoning went wrong.

Safety:
- Stay on schoolwork and study skills. Politely decline other requests.
- Never ask for personal information (full name, phone number, address, school, passwords) and tell the student not to share it.
- If a student says they are unsafe, being hurt, or thinking of hurting themselves, respond with care, encourage them to talk to a trusted adult or teacher straight away, and say that in Rwanda they can call the free child helpline 116."""

# A safety net that doesn't depend on the model: these always get the helpline in the answer.
UNSAFE = re.compile(
    r"suicid|kill (my ?self|me)|hurt(ing)? (my ?self|me)|self[- ]?harm|end my life|want to die|being (hit|beaten|abused)"
    r"|me tuer|me suicider|me faire du mal|envie de mourir|veux mourir|on me (frappe|bat)|abus(e|é)",
    re.I,
)


def reply_language(user, lang=None):
    return lang if lang in LANGUAGE_NAMES else (user.preferred_language if user.preferred_language in LANGUAGE_NAMES else "en")


def clean_history(history):
    """Validate prior turns sent by the browser: alternating user/assistant text, oldest first.

    Only the most recent turns that fit Santa's memory are kept (whole question-and-answer pairs)."""
    if not history:
        return []
    if not isinstance(history, list):
        raise ValidationError({"history": _("Must be a list of messages.")})
    history = history[-MAX_HISTORY_MESSAGES:]
    if history and not (isinstance(history[0], dict) and history[0].get("role") == "user"):
        history = history[1:]
    cleaned = []
    for i, item in enumerate(history):
        role = item.get("role") if isinstance(item, dict) else None
        content = item.get("content") if isinstance(item, dict) else None
        expected = "user" if i % 2 == 0 else "assistant"
        if role != expected or not isinstance(content, str) or not content.strip():
            raise ValidationError({"history": _("Messages must alternate between the student and Santa.")})
        cleaned.append({"role": role, "content": content[:HISTORY_MESSAGE_CHARS]})
    if cleaned and cleaned[-1]["role"] != "assistant":
        raise ValidationError({"history": _("The history must end with a reply from Santa.")})
    while len(cleaned) > 2 and sum(len(m["content"]) for m in cleaned) > HISTORY_CHARS:
        cleaned = cleaned[2:]
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


def open_exam(user):
    """The timed test or exam-mode quiz this student still has open, if any.

    While there is one, Santa (in a lesson, on the Santa page or in another tab) can't help with anything,
    until it is submitted or its time runs out."""
    open_attempts = (
        Attempt.objects.filter(user=user, status=Attempt.Status.IN_PROGRESS).select_related("quiz").order_by("-started_at")
    )
    reachable = set(assessment_services.visible_quizzes(user).values_list("pk", flat=True))
    for attempt in open_attempts:
        if assessment_services.finalize_if_expired(attempt):
            continue
        if not (attempt.deadline is not None or attempt.quiz.feedback_mode == Quiz.FeedbackMode.AFTER_SUBMIT):
            continue
        if attempt.quiz_id not in reachable or not access.can_open(user, attempt.quiz):
            # The student can no longer open it (archived, left the class, access ended): close it with
            # what was answered, as the attempt page does, so it can't keep Santa off for good.
            assessment_services.submit_attempt(attempt)
            continue
        return attempt
    return None


@dataclass
class Context:
    """What the student is looking at, and what Santa may know about it."""

    user: object
    language: str  # "en" or "fr": the language Santa answers in
    text: str = ""
    lesson: object = None
    attempt: object = None
    question: object = None
    subject: object = None


def build_context(user, lesson_slug=None, attempt_id=None, question_id=None, lang=None, subject_code=None):
    """The Context for what the student is looking at.

    `lang` is the language the student is reading in (defaults to their saved preference).
    `subject_code` is the subject chosen on the Santa page, when there is no lesson or quiz."""
    code = reply_language(user, lang)
    context = Context(user=user, language=code)
    grade = user.grade or "secondary school"
    sections = [
        f"The student is in {grade}. Reply in {LANGUAGE_NAMES[code]} unless the student writes in another language; "
        "then reply in theirs."
    ]

    if subject_code:
        context.subject = Subject.objects.filter(code=subject_code).first()
        if context.subject is None:
            raise NotFound(_("Unknown subject."))
        sections.append(
            f"The student opened the Santa page and chose the subject {context.subject.name}. Help with questions about "
            "it at their grade; if they ask about another school subject, help with that too."
        )

    if lesson_slug:
        lesson = visible_lessons(user).select_related("unit__subject").filter(slug=lesson_slug).first()
        if lesson is None:
            raise NotFound(_("Lesson not found."))
        context.lesson = lesson
        unit = lesson.unit
        translation_row = lesson.translations.filter(language=code).first() if code != "en" else None
        title = translation_row.title if translation_row else lesson.title
        sections.append(
            f'The student is studying the lesson "{title}" ({unit.subject.name}, {unit.grade}, unit {unit.number}: '
            f"{unit.title}). Passages from it are below."
        )

    if attempt_id:
        attempt = Attempt.objects.select_related("quiz", "quiz__subject").filter(pk=attempt_id, user=user).first()
        if attempt is None:
            raise NotFound(_("Attempt not found."))
        context.attempt = attempt
        assessment_services.finalize_if_expired(attempt)
        in_progress = attempt.status == Attempt.Status.IN_PROGRESS
        if in_progress and (attempt.deadline or attempt.quiz.feedback_mode == Quiz.FeedbackMode.AFTER_SUBMIT):
            raise PermissionDenied(_("Santa is switched off during exams and timed tests. Good luck!"))
        if question_id:
            try:
                question_id = int(question_id)
            except (TypeError, ValueError):
                raise ValidationError({"question": _("Unknown question.")})
            if question_id not in attempt.question_order:
                raise NotFound(_("That question is not part of this attempt."))
            question = Question.objects.prefetch_related("choices").get(pk=question_id)
            context.question = question
            answer = attempt.answers.filter(question=question).prefetch_related("selected_choices").first()
            block = [
                f"Quiz: {attempt.quiz.title} ({attempt.quiz.subject.name}, {attempt.quiz.grade}).",
                _question_text(attempt, question),
                _student_answer_text(question, answer),
            ]
            if assessment_services.can_see_solutions(attempt, answer):
                block.append(_solution_text(question, answer))
                block.append("The student has finished this question and may see the answer.")
            else:
                block.append(
                    "The student is STILL ANSWERING this practice question. Do not reveal or confirm the answer; give hints only."
                )
            sections.append("<quiz_question>\n" + "\n\n".join(block)[:QUESTION_CHARS] + "\n</quiz_question>")
        else:
            sections.append(f'The student is working on the quiz "{attempt.quiz.title}".')

    context.text = "\n\n".join(sections)
    return context


@dataclass
class Prepared:
    """A checked question, ready for Santa."""

    context: Context
    message: str
    history: list
    prompt: str  # the student's turn: context, lesson passages and the question
    own: list  # passages of the open lesson, in reading order
    others: list  # passages of other lessons, best first

    @property
    def sources(self):
        return retrieval.sources(self.own + self.others)


def _passage_block(passage, number=None):
    label = f'"{passage.title}"' + (f" - {passage.heading}" if passage.heading else "")
    if number is not None:
        label = f"[{number}] {label} ({passage.subject}, {passage.grade})"
    return f"{label}\n{passage.text}"


def compose(context, message, own, others):
    """The student's turn: everything about this request, then the question itself."""
    parts = ["<context>\n" + context.text + "\n</context>"]
    if own:
        parts.append("<open_lesson>\n" + "\n\n".join(_passage_block(p) for p in own) + "\n</open_lesson>")
    if others:
        blocks = "\n\n".join(_passage_block(p, i) for i, p in enumerate(others, 1))
        parts.append("<lesson_passages>\n" + blocks + "\n</lesson_passages>")
    parts.append("Student's question:\n" + message)
    return "\n\n".join(parts)


def prepare(user, message, history=None, lesson_slug=None, attempt_id=None, question_id=None, lang=None, subject_code=None):
    """Check a question and gather what Santa may see. Raises DRF errors (400, 403, 404)."""
    message = (message or "").strip()
    if not message:
        raise ValidationError({"message": _("Write a question for Santa.")})
    if len(message) > MAX_MESSAGE_CHARS:
        raise ValidationError({"message": _("Please keep questions under %(n)s characters.") % {"n": MAX_MESSAGE_CHARS}})
    history = clean_history(history)
    context = build_context(user, lesson_slug, attempt_id, question_id, lang, subject_code)
    exam = open_exam(user)
    if exam is not None:
        detail = _("Santa is switched off while you have an exam or timed test open (“%(quiz)s”). Submit it to use Santa again.")
        raise PermissionDenied({"detail": detail % {"quiz": exam.quiz.title}, "attempt": exam.pk})
    query = message
    if context.question is not None:
        query += "\n" + context.question.prompt
    subject = context.subject or (context.attempt.quiz.subject if context.attempt else None)
    used = sum(len(m["content"]) for m in history) + len(context.text) + len(message)
    while history and used > TURN_CHARS - MIN_PASSAGE_CHARS:
        used -= len(history[0]["content"]) + len(history[1]["content"])
        history = history[2:]
    budget = max(MIN_PASSAGE_CHARS, min(PASSAGE_CHARS, TURN_CHARS - used))
    own, others = retrieval.search(
        user,
        query,
        context.language,
        lesson=context.lesson,
        subject_id=subject.pk if subject else None,
        budget=budget,
        lesson_budget=min(OPEN_LESSON_CHARS, budget),
    )
    return Prepared(context, message, history, compose(context, message, own, others), own, others)


def status(user):
    """What the app shows: {enabled, reason, state, exam}.

    state: "ready", "loading" (the model is starting), "unavailable" (its server isn't answering),
    "not_installed" (Santa answers from the lessons only), or "exam" (switched off by an open exam)."""
    if not access.has_premium(user):
        return {"enabled": False, "reason": "subscription_required", "state": "", "exam": None}
    exam = open_exam(user)
    if exam is not None:
        return {"enabled": True, "reason": "", "state": "exam", "exam": {"attempt": exam.pk, "quiz": exam.quiz.title}}
    health = llm.health()
    return {"enabled": True, "reason": "", "state": "unavailable" if health == "unreachable" else health, "exam": None}


# --- Answering ------------------------------------------------------------------------------


@dataclass
class _Answer:
    parts: list = field(default_factory=list)
    tools: list = field(default_factory=list)
    finish: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    after_tool: bool = False

    @property
    def text(self):
        return "".join(self.parts)

    def emit(self, text):
        if not text:
            return
        if self.after_tool and self.parts and not self.text[-1:].isspace():
            self.parts.append("\n\n")
            yield {"type": "delta", "text": "\n\n"}
        self.after_tool = False
        self.parts.append(text)
        yield {"type": "delta", "text": text}


def _round(payload, stream, deadline, answer):
    """One request to the model. Yields events as the text arrives; returns the llm.Reply."""
    if not stream:
        reply = llm.chat(payload, deadline)
        yield from answer.emit(reply.content)
        return reply
    chunks = llm.chat_stream(payload, deadline)
    try:
        while True:
            try:
                text = next(chunks)
            except StopIteration as done:
                return done.value
            if text:
                yield from answer.emit(text)
            else:
                yield {"type": "ping"}
    finally:
        chunks.close()  # the student pressed Stop: close the connection so the model stops too


def _run_tool(call):
    try:
        arguments = json.loads(call["arguments"] or "{}")
    except ValueError:
        arguments = call["arguments"]  # a small model may send the bare expression
    if isinstance(arguments, dict):
        arguments = arguments.get("expression", "")
    expression = str(arguments if isinstance(arguments, (str, int, float)) else "").strip()
    if call["name"] != "calculate":
        return expression, "error: unknown tool"
    if not expression:
        return expression, "error: give an expression, for example 3 * (4 + 5)"
    return expression, calculator.calculate(expression)


def _shrink(prepared):
    """Make the request smaller (no history, only the best passage). False when there is nothing to drop."""
    if not prepared.history and len(prepared.own) + len(prepared.others) <= 1:
        return False
    prepared.history = []
    prepared.own, prepared.others = prepared.own[:1], [] if prepared.own else prepared.others[:1]
    prepared.prompt = compose(prepared.context, prepared.message, prepared.own, prepared.others)
    return True


def _from_model(prepared, stream, deadline, answer):
    """Ask the model. When the question with its context doesn't fit one of the model server's slots (a
    model whose words are cut into more tokens than expected), ask once more with less context."""
    try:
        yield from _ask_model(prepared, stream, deadline, answer, tools=True)
    except llm.TooLong:
        if answer.text or answer.tools or not _shrink(prepared):
            raise
        log.info("Santa's question did not fit a model slot; asking again with less context")
        yield from _ask_model(prepared, stream, deadline, answer, tools=False)


def _ask_model(prepared, stream, deadline, answer, tools):
    """Ask the model, letting it use the calculator up to MAX_TOOL_ROUNDS times."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *prepared.history,
        {"role": "user", "content": prepared.prompt},
    ]
    tools = [calculator.TOOL] if tools else None
    for round_number in range(MAX_TOOL_ROUNDS + 1):
        payload = {
            "model": settings.SANTA_MODEL_NAME,
            "messages": messages,
            "max_tokens": settings.SANTA_MAX_TOKENS,
            "temperature": settings.SANTA_TEMPERATURE,
        }
        # The last round offers no tools, so the model has to answer.
        offered = tools if round_number < MAX_TOOL_ROUNDS else None
        if offered:
            payload["tools"] = offered
        try:
            reply = yield from _round(payload, stream, deadline, answer)
        except llm.ToolsRejected:
            if not offered:
                raise
            log.info("Santa's model server refused the calculator tool; asking again without it")
            tools = None
            payload.pop("tools")
            reply = yield from _round(payload, stream, deadline, answer)
        answer.prompt_tokens += reply.prompt_tokens
        answer.completion_tokens += reply.completion_tokens
        answer.finish = reply.finish_reason or answer.finish
        calls = [c for c in reply.tool_calls if c["name"]] if payload.get("tools") else []
        if not calls:
            return
        messages.append(
            {
                "role": "assistant",
                "content": reply.content or "",
                "tool_calls": [
                    {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                    for c in calls
                ],
            }
        )
        for call in calls:
            expression, result = _run_tool(call)
            answer.tools.append({"expression": expression, "result": result})
            answer.after_tool = True
            yield {"type": "tool", "name": call["name"], "expression": expression, "result": result}
            messages.append({"role": "tool", "tool_call_id": call["id"], "name": call["name"], "content": result})


def _excerpt(text, limit=FALLBACK_EXCERPT_CHARS):
    """The start of a passage, cut at a paragraph or sentence, with its maths and code blocks closed."""
    if len(text) > limit:
        cut = text[:limit]
        end = max(cut.rfind("\n\n"), cut.rfind(". "))
        text = (cut[: end + 1] if end > limit // 3 else cut).rstrip() + " ..."
    if text.count("```") % 2:
        text += "\n```"
    if text.replace("$$", "").count("$") % 2:
        text = text[: text.rfind("$")].rstrip() + " ..."
    if text.count("$$") % 2:
        text += "$$"
    return text


def _fallback_passages(prepared):
    """The passages to show without the model: the open lesson's best matches first, then other lessons."""
    terms = retrieval.tokens(prepared.message)
    own = list(prepared.own)
    if terms and own:
        index = retrieval.get_index()
        own.sort(key=lambda p: -index.score_passage(terms, p))
    return (own[:1] + prepared.others)[:FALLBACK_PASSAGES] if own else prepared.others[:FALLBACK_PASSAGES]


def _fallback_note(reason):
    if reason == "not_installed":
        return _("Santa's AI model is not installed on this school's server yet.")
    if reason == "loading":
        return _("Santa is still waking up. Ask again in a minute for a full answer.")
    if reason == "busy":
        return _("Santa is helping many students right now. Ask again in a minute for a full answer.")
    if reason == "too_long":
        return _("This is too long for Santa. Ask a shorter question, or start a new chat.")
    return _("Santa can't answer just now. Try again in a minute.")


def fallback_text(prepared, reason, passages):
    """An answer made of lesson passages, for when the model can't answer."""
    with translation.override(prepared.context.language):
        note = _fallback_note(reason)
        if not passages:
            return f"*{note}*\n\n" + _(
                "I couldn't find this in your lessons. Try other words, open the lesson on this topic, or ask your teacher."
            )
        blocks = [f"*{note}* " + _("Here is what your lessons say:")]
        for passage in passages:
            heading = f"**{passage.title}**" + (f" - {passage.heading}" if passage.heading else "")
            quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in _excerpt(passage.text).splitlines())
            blocks.append(f"{heading}\n\n{quoted}")
        return "\n\n".join(blocks)


def _safety_note(prepared, reply):
    if not UNSAFE.search(prepared.message) or "116" in reply:
        return ""
    with translation.override(prepared.context.language):
        return "\n\n" + _(
            "If you feel unsafe or someone is hurting you, please talk to a trusted adult or a teacher today. "
            "In Rwanda you can call the free child helpline 116."
        )


def _take(key, seconds):
    try:
        return cache.add(key, 1, seconds)
    except Exception:  # noqa: BLE001 - without the cache, Santa still answers, just without the limits
        log.warning("Santa's limits are off: the cache is not answering", exc_info=True)
        return True


def _release(key, token=None):
    try:
        if token is None or cache.get(key) == token:
            cache.delete(key)
    except Exception:  # noqa: BLE001
        pass


def _take_model_slot(seconds):
    """One of SANTA_PARALLEL places to ask the model, or None when all are in use."""
    token = uuid.uuid4().hex
    try:
        for i in range(max(1, settings.SANTA_PARALLEL)):
            key = f"santa:slot:{i}"
            if cache.add(key, token, seconds):
                return key, token
    except Exception:  # noqa: BLE001
        log.warning("Santa's limits are off: the cache is not answering", exc_info=True)
        return "", token
    return None


def answer(prepared, stream=False):
    """Santa's answer, as events: {"type": "start"}, then {"type": "delta", "text"} pieces (and
    {"type": "tool", ...} when the calculator was used, {"type": "ping"} to keep the line open), and at the end
    {"type": "done", "reply", "sources", "fallback", "tools"}; or one {"type": "error", "code", "detail"}.

    The exchange is logged when the answer ends, also when the student stops it half-way."""
    user = prepared.context.user
    # Longer than an answer can last: the time limit, plus a last wait for a model server gone silent.
    seconds = int(settings.SANTA_TIMEOUT_SECONDS) + llm.STREAM_READ_TIMEOUT + 15
    user_key = f"santa:user:{user.pk}"
    if not _take(user_key, seconds):
        yield {
            "type": "error",
            "code": "already_answering",
            "detail": _("Santa is still answering your last question. Wait for it to finish, or stop it."),
        }
        return
    slot = None
    result = _Answer()
    fallback = None
    logged = False
    deadline = time.monotonic() + settings.SANTA_TIMEOUT_SECONDS
    try:
        yield {"type": "start"}
        known = llm.cached_health()
        if not llm.installed() or known == "not_installed":
            fallback = "not_installed"
        elif known in ("loading", "unreachable"):
            fallback = "loading" if known == "loading" else "unavailable"
        else:
            slot = _take_model_slot(seconds)
            if slot is None:
                fallback = "busy"
        passages = prepared.own, prepared.others  # all of them, for an answer from the lessons
        if fallback is None:
            try:
                yield from _from_model(prepared, stream, deadline, result)
            except Exception as exc:  # noqa: BLE001 - whatever went wrong, the student still gets an answer
                code = exc.code if isinstance(exc, llm.SantaError) else "bug"
                if code == "bug":
                    log.exception("Santa's answer failed")
                else:
                    log.warning("Santa's model could not answer (%s): %s", code, exc)
                if not result.text.strip():
                    fallback = {"not_installed": "not_installed", "loading": "loading", "too_long": "too_long"}.get(
                        code, "unavailable"
                    )
                else:
                    result.finish = f"error:{code}"
                    with translation.override(prepared.context.language):
                        yield from result.emit(
                            "\n\n*" + _("(Santa stopped before finishing. Ask again, or check your lessons.)") + "*"
                        )
        sources = prepared.sources
        if fallback:
            prepared.own, prepared.others = passages
            passages = _fallback_passages(prepared)
            sources = retrieval.sources(passages)
            result = _Answer(finish=f"fallback:{fallback}")
            yield from result.emit(fallback_text(prepared, fallback, passages))
        else:
            with translation.override(prepared.context.language):
                if result.finish == "length":
                    yield from result.emit("\n\n*" + _("(Santa ran out of space. Ask me to continue.)") + "*")
                if not result.text.strip():
                    yield from result.emit(
                        _("I can't help with that one. Ask about your lessons or a practice question, or ask your teacher.")
                    )
        yield from result.emit(_safety_note(prepared, result.text))
        _log(prepared, result, fallback)
        logged = True
        yield {"type": "done", "reply": result.text, "sources": sources, "fallback": fallback, "tools": result.tools}
    finally:
        if not logged:  # stopped by the student, or the connection dropped
            result.finish = result.finish if result.finish.startswith("error") else "stopped"
            _log(prepared, result, fallback)
        if slot:
            _release(slot[0], slot[1])
        _release(user_key)


def _log(prepared, result, fallback):
    context = prepared.context
    TutorExchange.objects.create(
        user=context.user,
        lesson=context.lesson,
        attempt=context.attempt,
        question=context.question,
        subject=context.subject,
        message=prepared.message,
        reply=result.text,
        model="lessons" if fallback else settings.SANTA_MODEL_NAME[:64],
        stop_reason=(result.finish or "")[:32],
        input_tokens=result.prompt_tokens,
        output_tokens=result.completion_tokens,
    )


def ask(user, message, **kwargs):
    """Santa's whole answer at once: {"reply", "sources", "fallback", "tools"} (or {"error", "detail"})."""
    prepared = prepare(user, message, **kwargs)
    events = answer(prepared, stream=False)
    try:
        for event in events:
            if event["type"] == "error":
                return {"error": event["code"], "detail": event["detail"]}
            if event["type"] == "done":
                return {key: event[key] for key in ("reply", "sources", "fallback", "tools")}
    finally:
        events.close()  # frees this student's turn and the model slot now
    return {"error": "no_answer", "detail": ""}
