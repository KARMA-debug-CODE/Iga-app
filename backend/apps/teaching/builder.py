"""Assemble a Teaching Pack from checked content: the question bank, the lesson, the unit and the class's
results (insight.py). No AI and no network here; Santa's optional suggestions are added by polish.py and
apply_polish(). See docs/superpowers/specs/2026-10-23-teaching-packs-design.md, section 5."""

import re

from django.conf import settings
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.assessments.models import Question
from apps.core.constants import ContentStatus
from apps.curriculum.models import Resource, Unit

from .insight import current_students, question_stats, unit_insight, unit_label

DOCUMENT_VERSION = 1
LEVELS = (("support", 1), ("core", 2), ("stretch", 3))
LEVEL_NAMES = {"support": gettext_lazy("support"), "core": gettext_lazy("core"), "stretch": gettext_lazy("stretch")}
SELF_MARKING_TYPES = {Question.Type.MCQ, Question.Type.MULTI, Question.Type.TRUE_FALSE, Question.Type.NUMERIC}
MAX_ACTIVITIES = 3
MAX_REFERENCES = 3
MAX_EVALUATION_QUESTIONS = 3
_HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"\*(.+?)\*|(?<!\w)_(.+?)_(?!\w)")
_MATHS = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$", re.DOTALL)
_MATHS_SPACE = re.compile(r"\\[,;:! ]")
_MATHS_ESCAPE = re.compile(r"\\([%&#_])")
_DEGREES = re.compile(r"\^\s*\{?\s*\\circ\s*\}?")
_WRAPPER = re.compile(
    r"\\(?:text|textbf|textit|mathrm|mathbf|mathit|mathbb|mathcal|operatorname|boldsymbol|vec|hat|bar|overline|"
    r"underline|overrightarrow|emph)\s*\{([^{}]*)\}"
)
_FRAC = re.compile(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
_ROOT = re.compile(r"\\sqrt\s*(?:\[(\d+)\])?\s*\{([^{}]*)\}")
_FUNCTION = re.compile(r"\\(sin|cos|tan|cot|sec|csc|log|ln|exp|lim|max|min)(?![A-Za-z])")
_FUNCTION_BRACKET = re.compile(r"\b(sin|cos|tan|cot|sec|csc|log|ln|exp) \(")
_COMMAND = re.compile(r"\\([A-Za-z]+)")
_POWER = re.compile(r"\^\s*(?:\{([^{}]*)\}|([^\s{}]))")
_SYMBOLS = {
    "times": "×", "div": "÷", "cdot": "·", "pm": "±", "mp": "∓", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥",
    "ne": "≠", "neq": "≠", "approx": "≈", "equiv": "≡", "propto": "∝", "infty": "∞", "circ": "°", "degree": "°",
    "to": "→", "rightarrow": "→", "leftarrow": "←", "Rightarrow": "⇒", "leftrightarrow": "<->",
    "rightleftharpoons": "⇌", "angle": "∠", "triangle": "△", "perp": "⊥", "parallel": "∥", "in": "∈", "cup": "∪",
    "cap": "∩", "subset": "⊂", "emptyset": "∅", "sum": "Σ", "int": "∫", "ldots": "…", "dots": "…", "cdots": "⋯",
    "quad": " ", "qquad": " ", "left": "", "right": "", "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ",
    "Delta": "Δ", "epsilon": "ε", "theta": "θ", "lambda": "λ", "mu": "μ", "pi": "π", "rho": "ρ", "sigma": "σ",
    "Sigma": "Σ", "tau": "τ", "phi": "φ", "omega": "ω", "Omega": "Ω",
}  # fmt: skip
_SUPERSCRIPTS = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
_ROOT_SIGNS = {None: "√", "2": "√", "3": "∛", "4": "∜"}


def question_payload(question):
    """A question with its answers: the pack is a teacher-only document (student output never shows them)."""
    return {
        "id": question.id,
        "type": question.type,
        "prompt": question.prompt,
        "choices": [{"id": c.id, "text": c.text, "is_correct": c.is_correct} for c in question.choices.all()],
        "numeric_answer": question.numeric_answer,
        "accepted_answers": question.accepted_answers or [],
        "explanation": question.explanation,
        "marking_guide": question.marking_guide,
        "marks": float(question.marks),
        "difficulty": question.difficulty,
    }


def priority_ids(insight):
    """Question ids to put first: the misconceptions in order, then the hardest questions."""
    ids = [m["question_id"] for m in insight["misconceptions"]]
    ids += [h["question_id"] for h in insight["hardest"] if h["question_id"] not in ids]
    return ids


def _eligible(unit):
    return list(Question.objects.filter(unit=unit, status=ContentStatus.PUBLISHED).prefetch_related("choices").order_by("id"))


def _mastered(stat):
    return stat.answered >= settings.TEACHING_MIN_STUDENTS and stat.correct_share >= settings.TEACHING_MASTERED_SHARE


def _not_mastered(questions, stats):
    return [q for q in questions if not (q.id in stats and _mastered(stats[q.id]))]


def _self_marking(question):
    return question.type in SELF_MARKING_TYPES or (question.type == Question.Type.SHORT and bool(question.accepted_answers))


def select_worksheet(unit, stats, priority):
    """{"support", "core", "stretch": [Question], "notes": [str]}: by difficulty 1/2/3; misconceptions and hardest
    first, then questions the class has not answered, then the rest. Short levels are noted, never backfilled."""

    def rank(question):
        if question.id in priority:
            return (0, priority.index(question.id), question.id)
        stat = stats.get(question.id)
        return (1 if stat is None or not stat.answered else 2, 0, question.id)

    pool = _not_mastered(_eligible(unit), stats)
    size = settings.TEACHING_WORKSHEET_PER_LEVEL
    sheet = {"notes": []}
    for name, difficulty in LEVELS:
        level = sorted((q for q in pool if q.difficulty == difficulty), key=rank)[:size]
        sheet[name] = level
        if not level:
            sheet["notes"].append(_("No %(level)s questions exist for this unit yet.") % {"level": LEVEL_NAMES[name]})
        elif len(level) < size:
            # Two messages rather than ngettext: scripts/messages.py extracts plain gettext calls only.
            if len(level) == 1:
                note = _("Only %(count)s %(level)s question exists for this unit.")
            else:
                note = _("Only %(count)s %(level)s questions exist for this unit.")
            sheet["notes"].append(note % {"count": len(level), "level": LEVEL_NAMES[name]})
    return sheet


def select_quiz(unit, stats, priority, data_enough):
    """(questions, is_diagnostic): self-marking questions only. With data, aimed at what the class gets wrong;
    without, a diagnostic spread across difficulties 1, 2, 3 in turn."""
    pool = [q for q in _not_mastered(_eligible(unit), stats) if _self_marking(q)]
    size = settings.TEACHING_QUIZ_SIZE
    if data_enough:
        ordered = sorted(pool, key=lambda q: (0, priority.index(q.id)) if q.id in priority else (1, q.id))
        return ordered[:size], False
    buckets = [[q for q in pool if q.difficulty == difficulty] for _name, difficulty in LEVELS]
    rest = [q for q in pool if q.difficulty not in (1, 2, 3)]
    picked = []
    while len(picked) < size and any(buckets):
        for bucket in buckets:
            if bucket and len(picked) < size:
                picked.append(bucket.pop(0))
    return (picked + rest)[:size], True


def default_lesson(unit):
    return unit.lessons.filter(status=ContentStatus.PUBLISHED).order_by("order", "id").first()


def _french_lesson(lesson):
    return next((t for t in lesson.translations.all() if t.language == "fr"), None)


def _lesson_text(lesson, lang):
    """(title, body) in the pack language when a translation exists."""
    if lang == "fr":
        translation_fr = _french_lesson(lesson)
        if translation_fr:
            return translation_fr.title, translation_fr.body
    return lesson.title, lesson.body


def _grouped(part):
    part = part.strip()
    return f"({part})" if re.search(r"[\s+\-×÷·=/]", part) else part


def _power(match):
    exponent = match.group(1) if match.group(1) is not None else match.group(2)
    if exponent and all(c in "0123456789+-=()n" for c in exponent):
        return exponent.translate(_SUPERSCRIPTS)
    return "^" + (exponent if len(exponent) == 1 else f"({exponent})")


def _root(match):
    sign = _ROOT_SIGNS.get(match.group(1))
    if sign is None:
        return f"{_grouped(match.group(2))}^(1/{match.group(1)})"
    return sign + _grouped(match.group(2))


def _maths_words(expression):
    """LaTeX as text a teacher can read on paper: \\frac{3}{4} -> 3/4, x^2 -> x², \\times -> ×. Subscripts stay as _2."""
    text = _MATHS_ESCAPE.sub(r"\1", _MATHS_SPACE.sub(" ", expression))
    text = _DEGREES.sub("°", text)
    previous = None
    while previous != text:  # innermost first, so fractions and roots inside each other read right
        previous = text
        text = _WRAPPER.sub(r"\1", text)
        text = _FRAC.sub(lambda m: f"{_grouped(m.group(1))}/{_grouped(m.group(2))}", text)
        text = _ROOT.sub(_root, text)
    text = _FUNCTION.sub(r"\1 ", text)
    text = _COMMAND.sub(lambda m: _SYMBOLS.get(m.group(1), m.group(1)), text)
    text = _POWER.sub(_power, text)
    text = _FUNCTION_BRACKET.sub(r"\1(", text.replace("{", "").replace("}", ""))
    return " ".join(text.split())


def _plain(text):
    """Lesson or question text as plain words for the plan: maths read as text, no code ticks or emphasis, but
    subscripts such as 10_2 kept."""
    text = _MATHS.sub(lambda m: _maths_words(m.group(1) or m.group(2)), text)
    text = _BOLD.sub(r"\1", text.replace("$", "").replace("`", ""))
    text = _ITALIC.sub(lambda m: m.group(1) or m.group(2), text)
    return " ".join(text.lstrip("#").split())


def _activities(lesson, lang, fallback_title):
    if lesson is None:
        return [fallback_title]
    title, body = _lesson_text(lesson, lang)
    headings = [_plain(h) for h in _HEADING.findall(body)]
    return [h for h in headings if h][:MAX_ACTIVITIES] or [title]


def _minutes(duration):
    introduction, conclusion = round(duration * 5 / 40), round(duration * 10 / 40)
    return introduction, duration - introduction - conclusion, conclusion


def _references(unit):
    official = Resource.objects.filter(
        kind=Resource.Kind.TEXTBOOK, is_official=True, status=ContentStatus.PUBLISHED, subject=unit.subject
    ).order_by("id")
    titles = list(official.filter(unit=unit).values_list("title", flat=True)[:MAX_REFERENCES])
    if not titles:
        titles = list(official.filter(grade=unit.grade, unit__isnull=True).values_list("title", flat=True)[:MAX_REFERENCES])
    return "\n".join(titles)


def _template_hook(insight, topic):
    if insight["misconceptions"]:
        return _(
            'Start with a class vote on this question: "%(question)s". Let learners give their reasons before you reveal the answer.'
        ) % {"question": _plain(insight["misconceptions"][0]["prompt"])}
    return _("Ask learners what they already know about %(topic)s and write their ideas on the board.") % {"topic": topic}


def lesson_plan(classroom, unit, lesson, teacher, insight, core_questions, lang):
    """The lesson plan in the competence-based curriculum layout; call inside translation.override(lang)."""
    unit_title = unit.title_fr if lang == "fr" and unit.title_fr else unit.title
    lesson_title = _lesson_text(lesson, lang)[0] if lesson else unit_title
    duration = settings.TEACHING_PERIOD_MINUTES
    introduction, development, conclusion = _minutes(duration)

    previous = Unit.objects.filter(subject=unit.subject, grade=unit.grade, number=unit.number - 1).first()
    intro_lines = [_template_hook(insight, lesson_title)]
    if previous:
        previous_title = previous.title_fr if lang == "fr" and previous.title_fr else previous.title
        intro_lines.append(_("Recall %(unit)s: ask two learners to say what they remember.") % {"unit": previous_title})

    misconceptions = list(insight["misconceptions"])
    activity_lines = []
    for number, title in enumerate(_activities(lesson, lang, unit_title), start=1):
        line = _("Activity %(number)s: %(title)s.") % {"number": number, "title": title}
        if misconceptions:
            line += " " + _misconception_note(misconceptions.pop(0))
        activity_lines.append(line)
    activity_lines += [_misconception_note(m) for m in misconceptions]

    return {
        "school": teacher.school.name if teacher.school_id else "",
        "teacher": teacher.display_name,
        "term": "",
        "date": timezone.localdate().isoformat(),
        "subject": unit.subject.localized_name(lang),
        "class_name": classroom.name,
        "lesson_number": str(lesson.order) if lesson else "",
        "duration": str(duration),
        "class_size": str(current_students(classroom).count()),
        "sen_learners": "",
        "unit_number": str(unit.number),
        "unit_title": unit_title,
        "key_unit_competence": unit.key_unit_competence,
        "lesson_title": lesson_title,
        "objective": _("By the end of this lesson, learners can explain and use %(topic)s.") % {"topic": lesson_title},
        "location": _("In the classroom"),
        "materials": _("The Iga worksheet (printed or on screen), the board, and the student's book."),
        "references": _references(unit),
        "steps": [
            {
                "name": "introduction",
                "minutes": introduction,
                "teacher": "\n".join(intro_lines),
                "learners": _("Vote, explain their choice and listen to each other."),
                "competences": _("Critical thinking, communication"),
            },
            {
                "name": "development",
                "minutes": development,
                "teacher": "\n".join(activity_lines),
                "learners": _("Work in pairs on the worksheet, then explain their answers to the class."),
                "competences": _("Problem solving, cooperation"),
            },
            {
                "name": "conclusion",
                "minutes": conclusion,
                "teacher": _("Summarise the key points of %(topic)s, then ask the evaluation questions.")
                % {"topic": lesson_title},
                "learners": _("Answer the evaluation questions and note what they still find difficult."),
                "competences": _("Lifelong learning"),
            },
        ],
        "evaluation": "\n".join(
            f"{i}. {_plain(question.prompt)}" for i, question in enumerate(core_questions[:MAX_EVALUATION_QUESTIONS], start=1)
        ),
        "self_evaluation": "",
    }


def _misconception_note(misconception):
    note = _('Address the misconception: many learners chose "%(wrong)s". The correct answer is "%(correct)s".') % {
        "wrong": _plain(misconception["wrong_choice"]),
        "correct": _plain(misconception["correct"]),
    }
    if misconception["explanation"]:
        note += " " + _plain(misconception["explanation"])
    return note


def template_polish(document):
    """The hook and the simpler explanation without Santa: what the plan already says."""
    misconceptions = document["insight"]["misconceptions"]
    return {
        "hook": document["plan"]["steps"][0]["teacher"].split("\n")[0],
        "simpler": misconceptions[0]["explanation"] if misconceptions else "",
        "ai": False,
    }


def build_pack(classroom, unit, lesson, teacher, lang):
    """The whole pack document (section 5.1 of the spec), in `lang`, JSON-serialisable."""
    with translation.override(lang):
        insight = unit_insight(classroom, unit, lang)
        stats = question_stats(classroom, unit)
        priority = priority_ids(insight)
        sheet = select_worksheet(unit, stats, priority)
        quiz, diagnostic = select_quiz(unit, stats, priority, insight["data_enough"])
        plan = lesson_plan(classroom, unit, lesson, teacher, insight, sheet["core"], lang)
        notes = []
        if lang == "fr" and (not unit.title_fr or (lesson is not None and _french_lesson(lesson) is None)):
            notes.append(_("Some content is only available in English."))
        document = {
            "version": DOCUMENT_VERSION,
            "language": lang,
            "classroom": {"id": classroom.id, "name": classroom.name, "grade": classroom.grade, "size": int(plan["class_size"])},
            "unit": {
                "id": unit.id,
                "label": unit_label(unit, lang),
                "number": unit.number,
                "title": plan["unit_title"],
                "key_unit_competence": unit.key_unit_competence,
            },
            "lesson": {"id": lesson.id, "slug": lesson.slug, "title": plan["lesson_title"]} if lesson else None,
            "insight": insight,
            "plan": plan,
            "worksheet": {
                **{name: [question_payload(q) for q in sheet[name]] for name, _difficulty in LEVELS},
                "notes": sheet["notes"],
            },
            "quiz": {"diagnostic": diagnostic, "questions": [question_payload(q) for q in quiz]},
            "notes": notes,
            "generated_at": timezone.localtime().isoformat(),
        }
        document["polish"] = template_polish(document)
    return document


def apply_polish(document, polish):
    """Store Santa's suggestions (or the templates); when they are Santa's, put them into the plan's text."""
    if polish.get("ai"):
        steps = document["plan"]["steps"]
        template_hook = document.get("polish", {}).get("hook", "")
        introduction = steps[0]["teacher"]
        steps[0]["teacher"] = (
            introduction.replace(template_hook, polish["hook"], 1)
            if template_hook in introduction
            else f"{polish['hook']}\n{introduction}"
        )
        if polish.get("simpler"):
            steps[1]["teacher"] += "\n" + _("A simpler way to explain it: %(text)s") % {"text": polish["simpler"]}
    document["polish"] = polish
    return document
