"""Upgrading an installation from one "ICT & Computer Science" subject to ICT and Computer Science: the
migration moves each old unit, with everything in it, to its new place, then load_curriculum loads the new
outline. Nothing a student or teacher made is lost, and no old or duplicate unit is left on the subject pages."""

import importlib
import json
from collections import Counter

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.assessments.models import Answer, Attempt, Question
from apps.classroom.models import Assignment, Classroom, Enrollment
from apps.core.content_loader import DEFAULT_CONTENT_DIR, import_quiz_file, load_all, load_lessons, load_units
from apps.curriculum.models import Lesson, LessonProgress, Resource, Subject, Unit

from .conftest import make_user

BEFORE = ("curriculum", "0006_resource_books")
MIGRATION = ("curriculum", "0007_computer_science")
OLD_UNITS = importlib.import_module("apps.curriculum.migrations.0007_computer_science").OLD_ICT_UNITS
OLD_NUMBERS = {  # lesson slug: its unit number before the split (the files now give the new numbers)
    "s1-ict-first-web-page": 5,
    "s2-ict-css-basics": 3,
    "s3-ict-javascript-intro": 2,
    "s4-ict-python-basics": 3,
}


def migrate(targets):
    MigrationExecutor(connection).migrate(targets)


@pytest.fixture
def before_the_split():
    """The database as it was before the split (the curriculum tables are the same, only the data differs)."""
    migrate([BEFORE])
    try:
        yield
    finally:
        migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def load_old_ict(tmp_path):
    """The old subject, its old units and the four ICT lessons and quizzes where they used to be."""
    Subject.objects.create(code="ict", name="ICT & Computer Science", name_fr="TIC et informatique", category="ict", order=4)
    old = {"ict": {grade: [title for title, _ in rows] for grade, rows in OLD_UNITS.items()}}
    (tmp_path / "units.json").write_text(json.dumps(old), encoding="utf-8")
    load_units(tmp_path / "units.json")
    lessons, quizzes = tmp_path / "lessons", tmp_path / "quizzes"
    lessons.mkdir()
    quizzes.mkdir()
    for slug, number in OLD_NUMBERS.items():
        text = (DEFAULT_CONTENT_DIR / "lessons" / f"{slug}.md").read_text(encoding="utf-8")
        lines = [f"unit: {number}" if line.startswith("unit:") else line for line in text.splitlines()]
        (lessons / f"{slug}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        quiz = json.loads((DEFAULT_CONTENT_DIR / "quizzes" / f"{slug}.json").read_text(encoding="utf-8"))
        quiz["unit"] = number
        (quizzes / f"{slug}.json").write_text(json.dumps(quiz), encoding="utf-8")
    load_lessons(lessons)
    return {slug: import_quiz_file(quizzes / f"{slug}.json")[0] for slug in OLD_NUMBERS}


@pytest.mark.django_db(transaction=True)
def test_upgrading_from_the_combined_subject_keeps_everything(before_the_split, tmp_path, client_for):
    quizzes = load_old_ict(tmp_path)
    ict = Subject.objects.get(code="ict")
    old_unit = {(u.grade, u.title): u for u in Unit.objects.filter(subject=ict)}
    html_unit = old_unit[("S1", "Your first web page: HTML")]
    assert html_unit.number == 5

    # A student's work: a finished quiz (so its questions are never rebuilt), a lesson read, homework.
    student = make_user("aline", grade="S1")
    teacher = make_user("mugabo", role="teacher", teacher_approved=True)
    client = client_for(student)
    attempt = client.post(f"/api/quizzes/{quizzes['s1-ict-first-web-page'].id}/start/", {}, format="json").data
    assert client.post(f"/api/attempts/{attempt['id']}/submit/", {}, format="json").status_code == 200
    html = Lesson.objects.get(slug="s1-ict-first-web-page")
    LessonProgress.objects.create(user=student, lesson=html)
    classroom = Classroom.objects.create(name="S1 ICT", grade="S1", subject=ict, teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=student)
    homework = [
        Assignment.objects.create(classroom=classroom, title="Read", lesson=html, created_by=teacher),
        Assignment.objects.create(classroom=classroom, title="Quiz", quiz=quizzes["s1-ict-first-web-page"], created_by=teacher),
    ]
    # A teacher's own work: in a unit that becomes Computer Science, and in units with no new equivalent.
    architecture = Lesson.objects.create(
        unit=old_unit[("S4", "Computer architecture")], slug="cpu-parts", title="Parts of a CPU", body="x", status="published"
    )
    architecture_question = Question.objects.create(
        subject=ict, grade="S4", unit=architecture.unit, type="short", prompt="What does ALU stand for?", status="published"
    )
    capstone = Lesson.objects.create(
        unit=old_unit[("S6", "Capstone project")], slug="my-capstone", title="Plan your project", body="x", status="published"
    )
    notes = Resource.objects.create(
        subject=ict, grade="S2", unit=old_unit[("S2", "Introduction to algorithms")], kind="notes", title="Algorithm notes"
    )
    attempts, answers = Attempt.objects.count(), Answer.objects.count()
    html_questions = set(quizzes["s1-ict-first-web-page"].questions.values_list("id", flat=True))

    migrate([MIGRATION])

    cs = Subject.objects.get(code="computer-science")
    ict.refresh_from_db()
    assert ict.name == "ICT" and cs.name == "Computer Science"
    # Each old unit moved with its content: same row, new place and title.
    html_unit.refresh_from_db()
    assert (html_unit.subject, html_unit.number, html_unit.title) == (ict, 6, "Your first web page: HTML")
    architecture.refresh_from_db()
    assert (architecture.unit.subject, architecture.unit.grade, architecture.unit.title) == (
        cs,
        "S4",
        "Computer architecture and assembly",
    )
    architecture_question.refresh_from_db()
    assert architecture_question.subject == cs and architecture_question.unit == architecture.unit
    # Units with no new equivalent: kept when they hold a teacher's work, after the new units; otherwise gone.
    capstone.refresh_from_db()
    assert (capstone.unit.title, capstone.unit.number) == ("Capstone project", 5)
    notes.refresh_from_db()
    assert notes.unit.title == "Introduction to algorithms" and notes.unit.number == 6
    assert not Unit.objects.filter(title__in=["Software engineering", "ICT and society", "Multimedia"]).exists()

    # Then the rest of the upgrade, as on a real server: every other migration (the icon column grows to hold icon
    # names), and load_curriculum.
    migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
    log = []
    load_all(log=log.append)

    # The subject pages show the new outline, with no leftover or duplicate unit.
    outline = json.loads((DEFAULT_CONTENT_DIR / "units.json").read_text(encoding="utf-8"))
    kept = {"Capstone project", "Introduction to algorithms"}
    for code in ("ict", "computer-science"):
        for grade, titles in outline[code].items():
            units = Unit.objects.filter(subject__code=code, grade=grade).order_by("number")
            assert [u.title for u in units if u.title not in kept] == titles, (code, grade)
            assert [u.number for u in units] == list(range(1, units.count() + 1)), (code, grade)
    assert not [key for key, n in Counter(Unit.objects.values_list("subject", "grade", "number")).items() if n > 1]
    assert [line for line in log if line.startswith("Kept")] == [
        "Kept ICT S2 · Unit 6: Introduction to algorithms (not in units.json, but it still has lessons, questions or books)",
        "Kept ICT S6 · Unit 5: Capstone project (not in units.json, but it still has lessons, questions or books)",
    ]

    # Nothing lost: lessons, progress, the attempt and its answers, homework.
    html = Lesson.objects.get(slug="s1-ict-first-web-page")
    assert html.unit == html_unit and LessonProgress.objects.filter(user=student, lesson=html).exists()
    assert Lesson.objects.filter(slug__in=["cpu-parts", "my-capstone", *OLD_NUMBERS]).count() == 6
    assert (Attempt.objects.count(), Answer.objects.count()) == (attempts, answers)
    quiz = quizzes["s1-ict-first-web-page"]
    quiz.refresh_from_db()
    assert quiz.unit == html_unit and set(quiz.questions.values_list("id", flat=True)) == html_questions
    # Its questions still point at the HTML unit (the loader alone would have left them on "Word processing").
    assert set(Question.objects.filter(id__in=html_questions).values_list("unit__title", flat=True)) == {
        "Your first web page: HTML"
    }
    assert all(Assignment.objects.filter(pk=a.pk).exists() for a in homework)
    s1 = client.get("/api/subjects/ict/", {"grade": "S1"}).data
    assert [u["title"] for u in s1["units"]] == outline["ict"]["S1"]
    assert s1["completed_count"] == 1


def test_units_dropped_from_units_json_go_unless_something_uses_them(tmp_path, subject):
    path = tmp_path / "units.json"
    path.write_text(json.dumps({"mathematics": {"S2": ["Ratios", "Graphs", "Vectors"]}}), encoding="utf-8")
    load_units(path)
    vectors = Unit.objects.get(title="Vectors")
    Lesson.objects.create(unit=vectors, slug="arrows", title="Arrows", body="x")

    path.write_text(json.dumps({"mathematics": {"S2": ["Ratios"]}}), encoding="utf-8")
    log = []
    load_units(path, log.append)
    assert list(Unit.objects.values_list("title", flat=True)) == ["Ratios", "Vectors"]
    assert log == ["Kept Mathematics S2 · Unit 3: Vectors (not in units.json, but it still has lessons, questions or books)"]


@pytest.mark.django_db
def test_a_new_installation_needs_no_upgrade():
    migration = importlib.import_module("apps.curriculum.migrations.0007_computer_science")
    from django.apps import apps

    migration.split_ict(apps, None)  # no subjects yet: nothing to do
    assert not Subject.objects.exists()
    load_all(log=lambda *_: None)
    migration.split_ict(apps, None)  # already on the new outline: nothing moves
    assert Unit.objects.filter(subject__code="ict", grade="S1").count() == 6
