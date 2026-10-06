import json

import pytest
from django.core.management import CommandError, call_command

from apps.core.content_loader import DEFAULT_CONTENT_DIR, ContentError, load_books, load_subjects
from apps.core.management.commands import check_book_links
from apps.curriculum.models import Resource

from .conftest import make_school, make_user

pytestmark = pytest.mark.django_db
BOOKS = DEFAULT_CONTENT_DIR / "books.json"


def book(**overrides):
    entry = {
        "id": "reb-mathematics-s2",
        "subject": "mathematics",
        "grades": ["S2"],
        "kind": "textbook",
        "official": True,
        "title": "Mathematics Senior 2 Student's Book",
        "publisher": "Rwanda Basic Education Board (REB)",
        "language": "en",
        "url": "https://elearning.reb.rw/example.pdf",
        "format": "pdf",
        "licence": "© REB, free to read",
        "description": "The official book.",
        "description_fr": "Le manuel officiel.",
    }
    entry.update(overrides)
    return entry


def write(tmp_path, books):
    path = tmp_path / "books.json"
    path.write_text(json.dumps({"books": books}), encoding="utf-8")
    return path


def test_every_subject_and_grade_has_an_official_textbook():
    units = json.loads((DEFAULT_CONTENT_DIR / "units.json").read_text(encoding="utf-8"))
    books = json.loads(BOOKS.read_text(encoding="utf-8"))["books"]
    official = {
        (b["subject"], grade)
        for b in books
        if b.get("official") and b["kind"] in ("textbook", "teacher_guide")
        for grade in b["grades"]
    }
    missing = [
        (code, grade)
        for code, grades in units.items()
        if not code.startswith("_")
        for grade in grades
        if (code, grade) not in official
    ]
    assert missing == []


def test_the_books_file_loads():
    load_subjects(DEFAULT_CONTENT_DIR / "subjects.json")
    assert load_books(BOOKS) >= 81
    assert not Resource.objects.exclude(url__startswith="https://").exists()
    assert not Resource.objects.filter(licence="").exists()


def test_loading_again_updates_books_and_removes_old_ones(tmp_path, subject):
    assert load_books(write(tmp_path, [book(id="a", grades=["S1", "S2"]), book(id="b")])) == 3
    teacher_upload = Resource.objects.create(subject=subject, kind="link", title="Teacher notes", url="https://example.org/")

    assert load_books(write(tmp_path, [book(id="a", grades=["S1"], title="New title")])) == 1
    assert list(Resource.objects.exclude(content_id="").values_list("content_id", "title")) == [("a@S1", "New title")]
    assert Resource.objects.filter(pk=teacher_upload.pk).exists()


@pytest.mark.parametrize(
    "bad",
    [
        {"url": "http://elearning.reb.rw/x.pdf"},
        {"subject": "astrology"},
        {"grades": ["S9"]},
        {"format": "epub"},
        {"language": "de"},
        {"licence": ""},
    ],
)
def test_bad_book_entries_are_refused(tmp_path, subject, bad):
    with pytest.raises(ContentError):
        load_books(write(tmp_path, [book(**bad)]))


def test_a_book_listed_twice_for_a_grade_is_refused(tmp_path, subject):
    with pytest.raises(ContentError):
        load_books(write(tmp_path, [book(id="a"), book(id="a")]))


def test_lessons_list_their_books_official_first_even_when_locked(client_for, lesson, tmp_path):
    unpaid = make_user("samuel", school=make_school("APADE", "Kicukiro"))
    open_book = book(
        id="open-algebra",
        official=False,
        title="Elementary Algebra",
        publisher="OpenStax",
        url="https://openstax.org/details/books/elementary-algebra-2e",
        format="web",
        licence="CC BY-NC-SA 4.0",
    )
    other_grade = book(id="reb-mathematics-s3", grades=["S3"], title="Mathematics Senior 3 Student's Book")
    load_books(write(tmp_path, [open_book, book(), other_grade]))

    data = client_for(unpaid).get(f"/api/lessons/{lesson.slug}/").data
    assert data["locked"]  # this student's school hasn't subscribed: the free REB books are still listed
    titles = [r["title"] for r in data["resources"]]
    assert titles == ["Mathematics Senior 2 Student's Book", "Elementary Algebra"]
    first = data["resources"][0]
    assert first["is_official"] and first["format"] == "pdf" and first["description_fr"] == "Le manuel officiel."
    assert data["unit"]["title_en"] == "Linear graphs"


def test_subject_page_books_come_official_first(client_for, student, subject, tmp_path):
    load_books(write(tmp_path, [book(id="open-x", official=False, title="A open book"), book()]))
    data = client_for(student).get("/api/resources/", {"subject": "mathematics", "grade": "S2"}).data
    rows = data["results"] if isinstance(data, dict) else data
    assert [r["title"] for r in rows] == ["Mathematics Senior 2 Student's Book", "A open book"]


def test_check_book_links_reports_broken_links(tmp_path, monkeypatch):
    path = write(tmp_path, [book(id="good", url="https://example.org/ok"), book(id="gone", url="https://example.org/gone")])
    monkeypatch.setattr(check_book_links, "check", lambda url: (url.endswith("ok"), "HTTP 404"))
    with pytest.raises(CommandError):
        call_command("check_book_links", "--file", str(path))
    call_command("check_book_links", "--file", str(path), "--subject", "physics")  # nothing to check: no error
