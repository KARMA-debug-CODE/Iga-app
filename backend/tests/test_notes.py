"""Bookmarks and private per-lesson notes."""

import pytest

from apps.curriculum.models import Lesson
from apps.notes import userdata
from apps.notes.models import LessonBookmark, LessonNote

from .conftest import make_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def free_lesson(unit):
    return Lesson.objects.create(unit=unit, slug="notes-lesson", title="Fractions", body="x", status="published", is_free=True)


def test_bookmarking_is_idempotent_and_listable(client_for, free_lesson):
    student = make_user("bk")
    client = client_for(student)
    first = client.post("/api/bookmarks/", {"lesson": free_lesson.slug}, format="json")
    assert first.status_code == 201
    client.post("/api/bookmarks/", {"lesson": free_lesson.slug}, format="json")  # again
    assert LessonBookmark.objects.filter(user=student).count() == 1
    listed = client.get("/api/bookmarks/").data
    rows = listed if isinstance(listed, list) else listed["results"]
    assert rows[0]["lesson"]["slug"] == free_lesson.slug
    assert client.delete(f"/api/bookmarks/{first.data['id']}/").status_code == 204
    assert LessonBookmark.objects.filter(user=student).count() == 0


def test_a_note_is_created_updated_and_cleared(client_for, free_lesson):
    student = make_user("note")
    client = client_for(student)
    created = client.post("/api/notes/", {"lesson": free_lesson.slug, "body": "Remember the sign rule"}, format="json")
    assert created.status_code == 201 and created.data["body"] == "Remember the sign rule"
    # Posting again for the same lesson updates the single note, never a second one.
    client.post("/api/notes/", {"lesson": free_lesson.slug, "body": "Updated"}, format="json")
    assert LessonNote.objects.filter(user=student).count() == 1
    assert LessonNote.objects.get(user=student).body == "Updated"
    # An empty body clears the note.
    client.post("/api/notes/", {"lesson": free_lesson.slug, "body": "   "}, format="json")
    assert LessonNote.objects.filter(user=student).count() == 0


def test_note_text_is_cleaned_and_length_limited(client_for, free_lesson):
    student = make_user("clean")
    client = client_for(student)
    # Zero-width characters are stripped (apps/core/text.py).
    client.post("/api/notes/", {"lesson": free_lesson.slug, "body": "a​b"}, format="json")
    assert LessonNote.objects.get(user=student).body == "ab"
    too_long = client.post("/api/notes/", {"lesson": free_lesson.slug, "body": "x" * 6000}, format="json")
    assert too_long.status_code == 400


def test_the_lesson_state_endpoint_reports_bookmark_and_note(client_for, free_lesson):
    student = make_user("state")
    client = client_for(student)
    empty = client.get(f"/api/my-notes/{free_lesson.slug}/").data
    assert empty["bookmarked"] is False and empty["note"] is None
    client.post("/api/bookmarks/", {"lesson": free_lesson.slug}, format="json")
    client.post("/api/notes/", {"lesson": free_lesson.slug, "body": "hi"}, format="json")
    state = client.get(f"/api/my-notes/{free_lesson.slug}/").data
    assert state["bookmarked"] is True and state["bookmark_id"] and state["note"]["body"] == "hi"


def test_notes_can_be_searched(client_for, unit):
    student = make_user("search")
    client = client_for(student)
    a = Lesson.objects.create(unit=unit, slug="l-a", title="Photosynthesis", body="x", status="published", is_free=True)
    b = Lesson.objects.create(unit=unit, slug="l-b", title="Osmosis", body="x", status="published", is_free=True)
    client.post("/api/notes/", {"lesson": a.slug, "body": "chlorophyll traps light"}, format="json")
    client.post("/api/notes/", {"lesson": b.slug, "body": "water moves across a membrane"}, format="json")
    hits = client.get("/api/notes/", {"q": "chlorophyll"}).data
    rows = hits if isinstance(hits, list) else hits["results"]
    assert len(rows) == 1 and rows[0]["lesson"]["slug"] == "l-a"
    # Searching the lesson title works too.
    by_title = client.get("/api/notes/", {"q": "Osmosis"}).data
    rows = by_title if isinstance(by_title, list) else by_title["results"]
    assert len(rows) == 1 and rows[0]["lesson"]["slug"] == "l-b"


def test_cannot_note_a_lesson_you_cannot_see(client_for, unit):
    teacher = make_user("t", role="teacher", teacher_approved=True)
    draft = Lesson.objects.create(unit=unit, slug="hidden", title="Secret", body="x", status="draft", author=teacher)
    student = make_user("outsider")
    client = client_for(student)
    assert client.post("/api/notes/", {"lesson": draft.slug, "body": "peek"}, format="json").status_code == 404
    assert client.post("/api/bookmarks/", {"lesson": draft.slug}, format="json").status_code == 404
    assert client.get(f"/api/my-notes/{draft.slug}/").status_code == 404


def test_notes_are_private_to_their_author(client_for, free_lesson):
    owner = make_user("owner")
    intruder = make_user("intruder")
    note = LessonNote.objects.create(user=owner, lesson=free_lesson, body="mine only")
    # The intruder's list and detail never show the owner's note.
    assert client_for(intruder).get("/api/notes/").data in ([], {"results": [], "count": 0, "next": None, "previous": None})
    assert client_for(intruder).get(f"/api/notes/{note.id}/").status_code == 404


def test_export_and_erase_cover_bookmarks_and_notes(free_lesson):
    student = make_user("export-notes")
    LessonBookmark.objects.create(user=student, lesson=free_lesson)
    LessonNote.objects.create(user=student, lesson=free_lesson, body="keep me")
    exported = userdata.export_for(student)
    assert len(exported["bookmarks"]) == 1 and exported["lesson_notes"][0]["body"] == "keep me"
    userdata.erase_for(student)
    assert not LessonBookmark.objects.filter(user=student).exists()
    assert not LessonNote.objects.filter(user=student).exists()
