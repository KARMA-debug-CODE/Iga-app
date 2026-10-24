"""Teaching Packs: assembling a pack from checked content (apps/teaching/builder.py)."""

import json

import pytest
from django.utils import translation

from apps.assessments.models import Question
from apps.curriculum.models import Lesson, LessonTranslation, Resource, Unit
from apps.teaching.builder import apply_polish, build_pack, default_lesson, select_quiz, select_worksheet
from apps.teaching.insight import question_stats

from .conftest import add_mcq
from .teaching_factories import class_with_students, mark_answer


def q(subject, unit, prompt, difficulty=2, **fields):
    question = add_mcq(subject, unit, prompt)
    Question.objects.filter(pk=question.pk).update(difficulty=difficulty, **fields)
    question.refresh_from_db()
    return question


def other_type(subject, unit, prompt, qtype, **fields):
    return Question.objects.create(subject=subject, grade=unit.grade, unit=unit, type=qtype, prompt=prompt, **fields)


@pytest.fixture
def classroom(teacher, subject):
    c, _students = class_with_students(teacher, subject, 3)
    return c


def steps(document):
    return {step["name"]: step for step in document["plan"]["steps"]}


def test_worksheet_levels_follow_difficulty(subject, unit):
    d1, d2, d3 = q(subject, unit, "easy", 1), q(subject, unit, "middle", 2), q(subject, unit, "hard", 3)
    sheet = select_worksheet(unit, {}, [])
    assert (sheet["support"], sheet["core"], sheet["stretch"]) == ([d1], [d2], [d3])


def test_misconception_questions_come_first(subject, unit):
    first, second = q(subject, unit, "first"), q(subject, unit, "second")
    assert select_worksheet(unit, {}, [second.id])["core"] == [second, first]


def test_drafts_and_mastered_questions_are_left_out(teacher, subject, unit):
    c, students = class_with_students(teacher, subject, 5)
    kept = q(subject, unit, "kept")
    q(subject, unit, "draft", status="draft")
    mastered = q(subject, unit, "mastered")
    for student in students:
        mark_answer(student, mastered, 1, choices=["4"])
    assert select_worksheet(unit, question_stats(c, unit), [])["core"] == [kept]


def test_short_levels_say_so_and_are_not_backfilled(settings, subject, unit):
    settings.TEACHING_WORKSHEET_PER_LEVEL = 5
    stretch = [q(subject, unit, f"hard{i}", 3) for i in range(2)]
    core = [q(subject, unit, f"core{i}", 2) for i in range(6)]
    with translation.override("en"):
        sheet = select_worksheet(unit, {}, [])
    assert sheet["stretch"] == stretch and sheet["core"] == core[:5] and sheet["support"] == []
    assert "Only 2 stretch questions exist for this unit." in sheet["notes"]
    assert "No support questions exist for this unit yet." in sheet["notes"]


def test_quiz_uses_only_self_marking_questions(subject, unit):
    mcq = q(subject, unit, "mcq")
    numeric = other_type(subject, unit, "numeric", Question.Type.NUMERIC, numeric_answer=4)
    short_ok = other_type(subject, unit, "short ok", Question.Type.SHORT, accepted_answers=["four"])
    other_type(subject, unit, "short no list", Question.Type.SHORT, accepted_answers=[])
    other_type(subject, unit, "essay", Question.Type.ESSAY)
    questions, diagnostic = select_quiz(unit, {}, [], True)
    assert questions == [mcq, numeric, short_ok] and diagnostic is False


def test_diagnostic_quiz_without_data(subject, unit):
    for difficulty in (1, 1, 2, 2, 3, 3):
        q(subject, unit, f"d{difficulty}", difficulty)
    questions, diagnostic = select_quiz(unit, {}, [], False)
    assert diagnostic is True
    assert [question.difficulty for question in questions] == [1, 2, 3, 1, 2, 3]


def test_plan_is_prefilled(teacher, subject, unit, lesson, classroom):
    Unit.objects.filter(pk=unit.pk).update(key_unit_competence="Use linear graphs to model situations.")
    unit.refresh_from_db()
    for i in range(4):
        Resource.objects.create(
            subject=subject,
            grade="S2",
            unit=unit,
            kind=Resource.Kind.TEXTBOOK,
            title=f"REB Maths S2 book {i}",
            url="https://example.org/book",
            is_official=True,
        )
    Resource.objects.create(
        subject=subject,
        grade="S2",
        unit=unit,
        kind=Resource.Kind.TEXTBOOK,
        title="Unofficial notes",
        url="https://example.org/notes",
        is_official=False,
    )
    plan = build_pack(classroom, unit, lesson, teacher, "en")["plan"]
    assert plan["key_unit_competence"] == "Use linear graphs to model situations."
    assert (plan["lesson_title"], plan["class_size"], plan["duration"]) == ("Linear graphs", "3", "40")
    assert (plan["school"], plan["teacher"], plan["unit_number"]) == (teacher.school.name, teacher.display_name, "1")
    assert plan["class_name"] == classroom.name and plan["subject"] == "Mathematics"
    assert len(plan["references"].splitlines()) == 3 and "Unofficial notes" not in plan["references"]
    assert plan["term"] == plan["sen_learners"] == plan["self_evaluation"] == ""


def test_blank_competence_stays_blank(teacher, unit, lesson, classroom):
    assert build_pack(classroom, unit, lesson, teacher, "en")["plan"]["key_unit_competence"] == ""


def test_step_minutes_scale_with_the_period(settings, teacher, unit, lesson, classroom):
    assert [s["minutes"] for s in build_pack(classroom, unit, lesson, teacher, "en")["plan"]["steps"]] == [5, 25, 10]
    settings.TEACHING_PERIOD_MINUTES = 80
    plan = build_pack(classroom, unit, lesson, teacher, "en")["plan"]
    assert [s["minutes"] for s in plan["steps"]] == [10, 50, 20] and plan["duration"] == "80"


def test_development_tackles_the_misconceptions(teacher, subject, unit, lesson):
    c, students = class_with_students(teacher, subject, 5, prefix="m")
    speed = add_mcq(subject, unit, "Speed?", correct="distance / time", wrong=("distance x time", "time / distance"))
    for student in students:
        mark_answer(student, speed, 0, choices=["distance x time"])
    development = steps(build_pack(c, unit, lesson, teacher, "en"))["development"]["teacher"]
    assert "distance x time" in development and "distance / time" in development


def test_introduction_recalls_the_previous_unit(teacher, subject, unit, classroom):
    angles = Unit.objects.create(subject=subject, grade="S2", number=2, title="Angles")
    triangles = Unit.objects.create(subject=subject, grade="S2", number=3, title="Triangles")
    assert "Angles" in steps(build_pack(classroom, triangles, None, teacher, "en"))["introduction"]["teacher"]
    assert angles.title not in steps(build_pack(classroom, unit, None, teacher, "en"))["introduction"]["teacher"]


def test_development_falls_back_when_the_lesson_has_no_headings(teacher, unit, classroom):
    plain = Lesson.objects.create(unit=unit, slug="plain", title="Reading graphs", body="Just text.", status="published")
    assert "Reading graphs" in steps(build_pack(classroom, unit, plain, teacher, "en"))["development"]["teacher"]
    marked = Lesson.objects.create(
        unit=unit,
        slug="marked",
        title="Speed",
        body="## The **speed** $v$\ntext\n### Not this\n## Second `code`",
        status="published",
    )
    development = steps(build_pack(classroom, unit, marked, teacher, "en"))["development"]["teacher"]
    assert "The speed v" in development and "Second code" in development and "Not this" not in development
    assert "**" not in development and "$" not in development and "`" not in development


def test_plan_without_a_lesson_uses_the_unit(teacher, unit, classroom):
    document = build_pack(classroom, unit, None, teacher, "en")
    assert document["lesson"] is None and document["plan"]["lesson_title"] == unit.title
    assert unit.title in steps(document)["development"]["teacher"]


def test_default_lesson_is_the_first_published(unit):
    Lesson.objects.create(unit=unit, slug="draft", title="Draft", body="x", order=1, status="draft")
    second = Lesson.objects.create(unit=unit, slug="b", title="B", body="x", order=2, status="published")
    Lesson.objects.create(unit=unit, slug="c", title="C", body="x", order=3, status="published")
    assert default_lesson(unit) == second


def test_french_pack_uses_french_titles_and_notes_the_gaps(teacher, unit, lesson, classroom):
    Unit.objects.filter(pk=unit.pk).update(title_fr="Graphiques linéaires")
    unit.refresh_from_db()
    LessonTranslation.objects.create(lesson=lesson, language="fr", title="Graphes", body="## Lire un graphe")
    document = build_pack(classroom, unit, lesson, teacher, "fr")
    assert (document["plan"]["unit_title"], document["plan"]["lesson_title"]) == ("Graphiques linéaires", "Graphes")
    assert document["notes"] == [] and "Lire un graphe" in steps(document)["development"]["teacher"]
    untranslated = Lesson.objects.create(unit=unit, slug="en-only", title="English only", body="x", status="published")
    assert len(build_pack(classroom, unit, untranslated, teacher, "fr")["notes"]) == 1


def test_pack_document_is_json_and_versioned(teacher, subject, unit, lesson, classroom):
    q(subject, unit, "core one")
    document = build_pack(classroom, unit, lesson, teacher, "en")
    json.dumps(document)
    assert document["version"] == 1 and document["language"] == "en" and document["polish"]["ai"] is False
    assert document["unit"]["id"] == unit.id and document["classroom"]["size"] == 3
    question = document["worksheet"]["core"][0]
    assert set(question) == {
        "id",
        "type",
        "prompt",
        "choices",
        "numeric_answer",
        "accepted_answers",
        "explanation",
        "marking_guide",
        "marks",
        "difficulty",
    }
    assert document["quiz"]["diagnostic"] is True and document["generated_at"]


def test_apply_polish_only_changes_text_when_ai(teacher, unit, lesson, classroom):
    document = build_pack(classroom, unit, lesson, teacher, "en")
    before = steps(document)["introduction"]["teacher"]
    apply_polish(document, {"hook": "HOOK!", "simpler": "SIMPLE!", "ai": False})
    assert steps(document)["introduction"]["teacher"] == before and document["polish"]["ai"] is False
    apply_polish(document, {"hook": "HOOK!", "simpler": "SIMPLE!", "ai": True})
    assert "HOOK!" in steps(document)["introduction"]["teacher"]
    assert "SIMPLE!" in steps(document)["development"]["teacher"] and document["polish"]["hook"] == "HOOK!"


def test_plan_text_has_no_maths_delimiters(teacher, subject, unit, lesson, classroom):
    q(subject, unit, "Convert $101101_2$ to base ten.")
    plan = build_pack(classroom, unit, lesson, teacher, "en")["plan"]
    assert plan["evaluation"] == "1. Convert 101101_2 to base ten."


def test_headings_keep_subscripts(teacher, unit, classroom):
    bases = Lesson.objects.create(
        unit=unit, slug="bases", title="Bases", body="## Bases $10_2$ and _place value_", status="published"
    )
    development = steps(build_pack(classroom, unit, bases, teacher, "en"))["development"]["teacher"]
    assert "Bases 10_2 and place value" in development


def test_a_single_question_is_singular(settings, subject, unit):
    settings.TEACHING_WORKSHEET_PER_LEVEL = 5
    q(subject, unit, "hard", 3)
    with translation.override("en"):
        notes = select_worksheet(unit, {}, [])["notes"]
    assert "Only 1 stretch question exists for this unit." in notes


def test_plan_text_reads_maths_as_words(teacher, subject, unit, lesson, classroom):
    q(subject, unit, r"Simplify $\frac{3}{4} \times 8$, $x^2 \div x^{-1}$ and $\sqrt{x+1}$.")
    q(subject, unit, r"Show $\sin\theta = \frac{\text{opposite}}{\text{hypotenuse}}$ for $30^\circ$.")
    q(subject, unit, r"Is $\frac{a+b}{2} \geq \sqrt{ab}$? Keep `my_var` and $H_2O$.")
    evaluation = build_pack(classroom, unit, lesson, teacher, "en")["plan"]["evaluation"].splitlines()
    assert evaluation == [
        "1. Simplify 3/4 × 8, x² ÷ x⁻¹ and √(x+1).",
        "2. Show sin θ = opposite/hypotenuse for 30°.",
        "3. Is (a+b)/2 ≥ √ab? Keep my_var and H_2O.",
    ]
