"""Load curriculum content from the plain files in backend/content/.

Content lives in files so teachers can contribute through pull requests and so
the same content can be re-imported into any environment. Every loader is
idempotent: running it twice updates rather than duplicates.

    content/subjects.json          subjects with names in English and French
    content/units.json             unit titles per subject per grade
    content/simulations.json       virtual-lab catalogue
    content/lessons/*.md           lessons (front matter + Markdown)
    content/translations/*.<lang>.md
    content/quizzes/*.json         practice quizzes
    content/exam_papers/*.json     exam papers (same format + a "paper" block)
"""

import json
from pathlib import Path

from django.db import transaction

from apps.assessments.models import Choice, ExamPaper, Question, Quiz, QuizQuestion
from apps.core.constants import GRADE_CODES, LANGUAGE_CODES, ContentStatus
from apps.curriculum.models import Lesson, LessonTranslation, Subject, Unit
from apps.simulations.models import Simulation

DEFAULT_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"


class ContentError(ValueError):
    pass


def parse_front_matter(text, source="<string>"):
    """Split '---\\nkey: value\\n---\\nbody' into (dict, body)."""
    if not text.startswith("---"):
        raise ContentError(f"{source}: missing front matter")
    try:
        _, header, body = text.split("---", 2)
    except ValueError:
        raise ContentError(f"{source}: unterminated front matter")
    meta = {}
    for line in header.strip().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ContentError(f"{source}: bad front-matter line {line!r}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key.strip()] = value
    return meta, body.strip() + "\n"


def load_subjects(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for order, item in enumerate(data):
        Subject.objects.update_or_create(
            code=item["code"],
            defaults={
                "name": item["name"],
                "name_fr": item.get("name_fr", ""),
                "description": item.get("description", ""),
                "category": item.get("category", Subject.Category.OTHER),
                "icon": item.get("icon", "📘"),
                "color": item.get("color", "#00A1DE"),
                "offered_o_level": item.get("o", True),
                "offered_a_level": item.get("a", True),
                "order": order,
            },
        )
    return len(data)


def load_units(path):
    """units.json, plus French titles from units.fr.json next to it (same structure) when present."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    french_path = path.with_name(path.stem + ".fr.json")
    french = json.loads(french_path.read_text(encoding="utf-8")) if french_path.exists() else {}
    count = 0
    for code, grades in data.items():
        if code.startswith("_"):
            continue
        subject = Subject.objects.get(code=code)
        for grade, titles in grades.items():
            if grade not in GRADE_CODES:
                raise ContentError(f"units.json: unknown grade {grade} for {code}")
            titles_fr = french.get(code, {}).get(grade, [])
            if titles_fr and len(titles_fr) != len(titles):
                raise ContentError(f"units.fr.json: {code} {grade} has {len(titles_fr)} titles, units.json has {len(titles)}")
            for number, title in enumerate(titles, start=1):
                title_fr = titles_fr[number - 1] if titles_fr else ""
                Unit.objects.update_or_create(
                    subject=subject, grade=grade, number=number, defaults={"title": title, "title_fr": title_fr}
                )
                count += 1
    return count


def load_simulations(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for order, item in enumerate(data):
        sim, _ = Simulation.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "provider": item["provider"],
                "provider_id": item["provider_id"],
                "description": item.get("description", ""),
                "grades": item.get("grades", []),
                "topics": item.get("topics", ""),
                "learning_goals": item.get("learning_goals", ""),
                "order": order,
            },
        )
        sim.subjects.set(Subject.objects.filter(code__in=item.get("subjects", [])))
    return len(data)


def _unit(subject_code, grade, number, source):
    try:
        return Unit.objects.get(subject__code=subject_code, grade=grade, number=int(number))
    except Unit.DoesNotExist:
        raise ContentError(f"{source}: no unit {number} for {subject_code} {grade}")


def load_lessons(directory, status=ContentStatus.PUBLISHED):
    count = 0
    for path in sorted(Path(directory).glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"), path.name)
        for key in ("slug", "subject", "grade", "unit", "title"):
            if not meta.get(key):
                raise ContentError(f"{path.name}: missing '{key}'")
        fields = {
            "unit": _unit(meta["subject"], meta["grade"], meta["unit"], path.name),
            "order": int(meta.get("order", 1)),
            "title": meta["title"],
            "summary": meta.get("summary", ""),
            "body": body,
            "video_url": meta.get("video", ""),
            "estimated_minutes": int(meta.get("minutes", 15)),
            # "access: free" opens a lesson to everyone; the rest need a school subscription.
            "is_free": meta.get("access", "premium").strip().lower() == "free",
        }
        # Re-running the loader updates the text but keeps a lesson an admin archived or unpublished.
        lesson, _ = Lesson.objects.update_or_create(
            slug=meta["slug"], defaults=fields, create_defaults={**fields, "status": status}
        )
        slugs = [s.strip() for s in meta.get("simulations", "").split(",") if s.strip()]
        sims = list(Simulation.objects.filter(slug__in=slugs))
        if len(sims) != len(slugs):
            missing = set(slugs) - {s.slug for s in sims}
            raise ContentError(f"{path.name}: unknown simulations {sorted(missing)}")
        lesson.simulations.set(sims)
        count += 1
    return count


def load_translations(directory):
    count = 0
    for path in sorted(Path(directory).glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"), path.name)
        if meta.get("language") not in LANGUAGE_CODES:
            raise ContentError(f"{path.name}: language must be one of {LANGUAGE_CODES}")
        lesson = Lesson.objects.get(slug=meta["slug"])
        LessonTranslation.objects.update_or_create(
            lesson=lesson,
            language=meta["language"],
            defaults={
                "title": meta["title"],
                "summary": meta.get("summary", ""),
                "body": body,
                "reviewed": meta.get("reviewed", "false").lower() == "true",
            },
        )
        count += 1
    return count


def _build_question(data, subject, grade, default_unit, source, source_name):
    qtype = data["type"]
    if qtype not in Question.Type.values:
        raise ContentError(f"{source_name}: unknown question type {qtype!r}")
    unit = default_unit
    if data.get("unit_ref"):
        ref = data["unit_ref"]
        unit = _unit(subject.code, ref["grade"], ref["unit"], source_name)
    question = Question.objects.create(
        subject=subject,
        grade=unit.grade if unit else grade,
        unit=unit,
        type=qtype,
        prompt=data["prompt"],
        explanation=data.get("explanation", ""),
        marks=data.get("marks", 1),
        numeric_answer=data.get("answer") if qtype == Question.Type.NUMERIC else None,
        numeric_tolerance=data.get("tolerance", 0),
        accepted_answers=data.get("accepted", []),
        marking_guide=data.get("marking_guide", ""),
        difficulty=data.get("difficulty", 2),
        source=source,
        status=ContentStatus.PUBLISHED,
    )
    if qtype == Question.Type.TRUE_FALSE:
        answer = data.get("answer")
        if not isinstance(answer, bool):
            raise ContentError(f'{source_name}: true_false questions need "answer": true/false')
        Choice.objects.create(question=question, text="True", is_correct=answer, order=0)
        Choice.objects.create(question=question, text="False", is_correct=not answer, order=1)
    elif qtype in (Question.Type.MCQ, Question.Type.MULTI):
        choices = data.get("choices", [])
        correct = sum(1 for c in choices if c.get("correct"))
        if len(choices) < 2 or correct == 0 or (qtype == Question.Type.MCQ and correct != 1):
            raise ContentError(f"{source_name}: bad choices for {data['prompt'][:40]!r}")
        for i, choice in enumerate(choices):
            Choice.objects.create(question=question, text=choice["text"], is_correct=bool(choice.get("correct")), order=i)
    elif qtype == Question.Type.NUMERIC and question.numeric_answer is None:
        raise ContentError(f"{source_name}: numeric question without an answer")
    return question


PAPER_KEY = ("subject", "level", "year", "paper_code")


def _paper_fields(paper, subject, fallback_title):
    return {
        "subject": subject,
        "level": paper["level"],
        "year": paper["year"],
        "paper_code": paper.get("paper_code", ""),
        "title": paper.get("title", fallback_title),
        "is_official": paper.get("is_official", False),
        "source_note": paper.get("source_note", ""),
        "paper_url": paper.get("paper_url", ""),
        "marking_guide_url": paper.get("marking_guide_url", ""),
    }


@transaction.atomic
def import_quiz_file(path, status=ContentStatus.PUBLISHED):
    """Import one quiz or exam-paper JSON file.

    Returns (quiz, created), or (exam_paper, created) for a PDF-only paper
    that has no digitised questions yet.
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    subject = Subject.objects.get(code=data["subject"])
    paper = data.get("paper")

    if paper and not data.get("questions"):
        fields = _paper_fields(paper, subject, data.get("title", ""))
        key = {k: fields.pop(k) for k in PAPER_KEY}
        # If the paper was already digitised, add the PDF links to that one instead of a second entry.
        digitised = ExamPaper.objects.filter(**key, quiz__isnull=False).first()
        if digitised:
            for name, value in fields.items():
                if value and (name not in ("title",) or not digitised.title):
                    setattr(digitised, name, value)
            digitised.save()
            return digitised, False
        return ExamPaper.objects.update_or_create(**key, quiz=None, defaults=fields)

    grade = data["grade"]
    default_unit = _unit(subject.code, grade, data["unit"], path.name) if data.get("unit") else None
    source = Question.Source.SAMPLE
    if paper and paper.get("is_official"):
        source = Question.Source.PAST_PAPER

    quiz_fields = {
        "description": data.get("description", ""),
        "unit": default_unit,
        "kind": data.get("kind", Quiz.Kind.PRACTICE),
        "time_limit_minutes": data.get("time_limit_minutes"),
        "shuffle_questions": data.get("shuffle_questions", True),
        "shuffle_choices": data.get("shuffle_choices", True),
        "feedback_mode": data.get("feedback_mode", Quiz.FeedbackMode.IMMEDIATE),
        "max_attempts": data.get("max_attempts"),
        "is_free": data.get("access", "premium") == "free",
    }
    quiz, created = Quiz.objects.update_or_create(
        title=data["title"],
        subject=subject,
        grade=grade,
        defaults=quiz_fields,
        create_defaults={**quiz_fields, "status": status},
    )

    # Questions are only rebuilt while nobody has attempted the quiz, so results stay valid.
    if created or not quiz.attempts.exists():
        old_ids = list(quiz.quiz_questions.values_list("question_id", flat=True))
        quiz.quiz_questions.all().delete()
        Question.objects.filter(id__in=old_ids, author__isnull=True, quiz_links__isnull=True).delete()
        for order, item in enumerate(data["questions"]):
            question = _build_question(item, subject, grade, default_unit, source, path.name)
            QuizQuestion.objects.create(quiz=quiz, question=question, order=order)

    if paper:
        fields = _paper_fields(paper, subject, data["title"])
        # A PDF-only entry for the same paper is merged into the digitised one.
        pdf_only = ExamPaper.objects.filter(quiz=None, **{k: fields[k] for k in PAPER_KEY}).first()
        if pdf_only:
            for name in ("paper_url", "marking_guide_url", "source_note"):
                fields[name] = fields[name] or getattr(pdf_only, name)
            for name in ("paper_file", "marking_guide_file"):
                if getattr(pdf_only, name):
                    fields[name] = getattr(pdf_only, name)
            pdf_only.delete()
        ExamPaper.objects.update_or_create(quiz=quiz, defaults=fields)
    return quiz, created


def load_all(content_dir=DEFAULT_CONTENT_DIR, log=print):
    content_dir = Path(content_dir)
    log(f"Subjects:     {load_subjects(content_dir / 'subjects.json')}")
    log(f"Units:        {load_units(content_dir / 'units.json')}")
    log(f"Simulations:  {load_simulations(content_dir / 'simulations.json')}")
    log(f"Lessons:      {load_lessons(content_dir / 'lessons')}")
    log(f"Translations: {load_translations(content_dir / 'translations')}")
    quizzes = sorted((content_dir / "quizzes").glob("*.json"))
    for path in quizzes:
        import_quiz_file(path)
    log(f"Quizzes:      {len(quizzes)}")
    papers = sorted((content_dir / "exam_papers").glob("*.json"))
    for path in papers:
        import_quiz_file(path)
    log(f"Exam papers:  {len(papers)}")
