import json

import pytest

from apps.assessments.models import ExamPaper, Question, Quiz
from apps.core.content_loader import ContentError, import_quiz_file, load_all, parse_front_matter
from apps.curriculum.models import Lesson, Subject, Unit

pytestmark = pytest.mark.django_db


def test_shipped_content_loads_and_is_idempotent():
    load_all(log=lambda *_: None)
    counts = (
        Subject.objects.count(),
        Unit.objects.count(),
        Lesson.objects.count(),
        Quiz.objects.count(),
        Question.objects.count(),
    )
    load_all(log=lambda *_: None)
    assert counts == (
        Subject.objects.count(),
        Unit.objects.count(),
        Lesson.objects.count(),
        Quiz.objects.count(),
        Question.objects.count(),
    )
    assert Subject.objects.count() == 15
    # Every grade has units in the core subjects.
    for code in ("mathematics", "physics", "chemistry", "biology", "ict", "english"):
        grades = set(Unit.objects.filter(subject__code=code).values_list("grade", flat=True))
        assert grades == {"S1", "S2", "S3", "S4", "S5", "S6"}, code
    # Sample papers are never presented as official.
    assert ExamPaper.objects.exists()
    assert not ExamPaper.objects.filter(is_official=True).exists()
    # Every multiple-choice question has exactly one right answer.
    for q in Question.objects.filter(type="mcq"):
        assert q.choices.filter(is_correct=True).count() == 1, q.prompt


def test_front_matter_parsing():
    meta, body = parse_front_matter('---\ntitle: "Hello: world"\nminutes: 5\n---\nBody', "x.md")
    assert meta == {"title": "Hello: world", "minutes": "5"}
    assert body == "Body\n"
    with pytest.raises(ContentError):
        parse_front_matter("no header", "x.md")


def test_importer_rejects_bad_mcq(tmp_path):
    load_all(log=lambda *_: None)
    bad = {
        "title": "Broken",
        "subject": "mathematics",
        "grade": "S1",
        "questions": [{"type": "mcq", "prompt": "?", "choices": [{"text": "a"}, {"text": "b"}]}],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ContentError):
        import_quiz_file(path)
    assert not Quiz.objects.filter(title="Broken").exists()


def test_official_paper_questions_are_tagged_past_paper(tmp_path):
    load_all(log=lambda *_: None)
    paper = {
        "paper": {"level": "O", "year": 2019, "title": "Mathematics 2019", "is_official": True, "source_note": "NESA"},
        "title": "Mathematics 2019",
        "subject": "mathematics",
        "grade": "S3",
        "kind": "past_paper",
        "questions": [{"type": "numeric", "prompt": "1+1", "answer": 2}],
    }
    path = tmp_path / "p.json"
    path.write_text(json.dumps(paper))
    quiz, created = import_quiz_file(path)
    assert created
    assert quiz.exam_paper.is_official
    assert quiz.questions.get().source == "past_paper"
