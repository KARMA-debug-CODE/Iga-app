"""Every view checks its input: malformed ids, query strings and bodies are a 400 (or 403/404), never a 500."""

import pytest
from django.http import QueryDict

from apps.accounts.models import User
from apps.classroom.models import Classroom
from apps.community.models import GroupMembership, Message, MessageReport, StudyGroup
from apps.core.validation import contains_nul
from apps.curriculum.models import Lesson

from .conftest import make_school, make_user
from .routes import api_routes, fill, view_methods

pytestmark = pytest.mark.django_db

# Values of the wrong type or shape for every field name the API reads.
JUNK_BODY = {
    "code": 12345,
    "student": "abc",
    "body": ["not", "text"],
    "reason": {"a": 1},
    "csv": 5,
    "confirm": "maybe",
    "hide": "maybe",
    "approve": "maybe",
    "id": "abc",
    "type": "nonsense",
    "assignment": "abc",
    "question": "abc",
    "choice_ids": "abc",
    "ids": "abc",
    "school": "abc",
    "months": "abc",
    "currency": 5,
    "marks": "abc",
    "history": "abc",
    "session": {"x": 1},
    "outcome": 5,
    "transaction_id": {"x": 1},
    "otp": 5,
    "password": 5,
    "identifier": ["a"],
}
# Junk the views must turn away themselves (a NUL character is refused before any view: see the NUL tests).
JUNK_QUERY = (
    "?unit=abc&quiz=abc&classroom=abc&year=abc&page=abc&grade=%01%7F&subject=..%2F&after=abc&scope=class"
    "&status=x&role=x&q=%27%3B--&lang=xx&district=%E2%80%AE"
)
BAD_IDS = ["abc", "99999999999999999999999", "-1", "1.5"]


@pytest.fixture
def everyone(db):
    school = make_school("Lycee", "Gasabo")
    return {
        "anonymous": None,
        "student": make_user("fuzzstudent"),
        "teacher": make_user("fuzzteacher", role=User.Role.TEACHER, teacher_approved=True),
        "parent": make_user("fuzzparent", role=User.Role.PARENT),
        "school_admin": make_user("fuzzschooladmin", role=User.Role.SCHOOL_ADMIN, school=school),
        "admin": make_user("fuzzadmin", role=User.Role.ADMIN),
    }


def test_no_route_crashes_on_malformed_input(client_for, everyone):
    crashes = []
    for name, user in everyone.items():
        client = client_for(user)
        client.raise_request_exception = False
        for route, callback in api_routes():
            for bad_id in BAD_IDS if "{" in route else [None]:
                url = fill(route, default=bad_id) if bad_id else fill(route)
                for method in view_methods(callback):
                    send = getattr(client, method.lower())
                    if method == "GET":
                        response = send(url + JUNK_QUERY)
                    else:
                        response = send(url + JUNK_QUERY, JUNK_BODY, format="json")
                    # 503 is a deliberate answer (the code runner isn't configured in tests), not a crash.
                    if response.status_code >= 500 and response.status_code != 503:
                        crashes.append((name, method, url, response.status_code))
    assert not crashes, crashes


def test_list_filters_with_bad_ids_are_refused_cleanly(client_for, teacher):
    client = client_for(teacher)
    for url in (
        "/api/lessons/?unit=abc",
        "/api/resources/?unit=abc",
        "/api/questions/?unit=abc",
        "/api/quizzes/?unit=abc",
        "/api/attempts/?quiz=abc",
        "/api/assignments/?classroom=abc",
        "/api/leaderboard/?scope=class&classroom=abc",
        "/api/exam-papers/?year=abc",
    ):
        response = client.get(url)
        assert response.status_code == 400, url


def test_review_approve_must_be_a_real_boolean(client_for, admin_user, unit):
    lesson = Lesson.objects.create(unit=unit, slug="draft", title="Draft", body="x", status="review")
    client = client_for(admin_user)
    # The text "false" used to count as "approve" (bool("false") is True) and published the lesson.
    response = client.post("/api/admin/review/decide/", {"type": "lesson", "id": lesson.id, "approve": "false"}, format="json")
    assert response.status_code == 200
    lesson.refresh_from_db()
    assert lesson.status == "draft"
    assert (
        client.post(
            "/api/admin/review/decide/", {"type": "lesson", "id": lesson.id, "approve": "maybe"}, format="json"
        ).status_code
        == 400
    )
    assert client.post("/api/admin/review/decide/", {"type": "user", "id": 1, "approve": True}, format="json").status_code == 400
    long_note = {"type": "lesson", "id": lesson.id, "approve": True, "note": "x" * 501}
    assert client.post("/api/admin/review/decide/", long_note, format="json").status_code == 400


def test_resolving_a_report_with_hide_false_does_not_hide(client_for, admin_user, student):
    group = StudyGroup.objects.create(name="G")
    GroupMembership.objects.create(group=group, user=student, role="owner")
    message = Message.objects.create(group=group, author=student, body="hello")
    report = MessageReport.objects.create(message=message, reporter=student, reason="r")
    response = client_for(admin_user).post(f"/api/admin/moderation/{report.id}/resolve/", {"hide": "false"}, format="json")
    assert response.status_code == 200
    message.refresh_from_db()
    assert not message.is_hidden


def test_roster_confirm_false_only_previews(client_for, teacher):
    classroom = Classroom.objects.create(name="S2 A", grade="S2", teacher=teacher)
    csv = "first_name,last_name\nAline,Uwase\n"
    response = client_for(teacher).post(
        f"/api/classes/{classroom.id}/import_roster/", {"csv": csv, "confirm": "false"}, format="json"
    )
    assert response.status_code == 200 and "created" not in response.data
    assert not User.objects.filter(first_name="Aline").exists()
    huge = client_for(teacher).post(f"/api/classes/{classroom.id}/import_roster/", {"csv": "x" * 100_001}, format="json")
    assert huge.status_code == 400


def test_text_fields_must_be_text_and_bounded(client_for, student, teacher):
    group = StudyGroup.objects.create(name="G")
    GroupMembership.objects.create(group=group, user=student, role="owner")
    client = client_for(student)
    assert client.post("/api/classes/join/", {"code": 123456}, format="json").status_code == 400
    assert client.post("/api/groups/join-by-code/", {"code": ["A"]}, format="json").status_code == 400
    assert client.post(f"/api/groups/{group.id}/messages/", {"body": {"x": 1}}, format="json").status_code == 400
    assert client.post(f"/api/groups/{group.id}/messages/", {"body": "x" * 2001}, format="json").status_code == 400
    note = {"title": "t", "body": "x" * 20001}
    assert client.post(f"/api/groups/{group.id}/notes/", note, format="json").status_code == 400
    assert client.patch(f"/api/groups/{group.id}/", {"description": "x" * 1001}, format="json").status_code == 400
    assert client.patch(f"/api/groups/{group.id}/", {"max_members": 30000}, format="json").status_code == 400
    assert client.patch(f"/api/groups/{group.id}/", {"max_members": 0}, format="json").status_code == 400
    classroom = Classroom.objects.create(name="S2 A", grade="S2", teacher=teacher)
    for bad in ("abc", True, -3, [1]):
        response = client_for(teacher).post(f"/api/classes/{classroom.id}/reset_password/", {"student": bad}, format="json")
        assert response.status_code == 400, bad


# --- NUL characters: PostgreSQL text can't hold them, so before the fix any query parameter or body value
# with one that reached the database was a 500 on PostgreSQL (and silently stored on SQLite).


def test_nul_characters_are_refused_on_every_route(client_for, everyone):
    crashes, accepted = [], []
    for name, user in everyone.items():
        client = client_for(user)
        client.raise_request_exception = False
        for route, callback in api_routes():
            url = fill(route, default="1")
            for method in view_methods(callback):
                send = getattr(client, method.lower())
                for target in (url + "?grade=%00&q=a%00b", url.rstrip("/") + "%00/"):
                    response = send(target) if method == "GET" else send(target, {}, format="json")
                    if response.status_code >= 500:
                        crashes.append((name, method, target, response.status_code))
                    elif "?" in target and response.status_code != 400:
                        accepted.append((name, method, target, response.status_code))
    assert not crashes, crashes
    assert not accepted, accepted


def test_nul_characters_in_bodies_are_refused(client_for, student):
    group = StudyGroup.objects.create(name="G")
    GroupMembership.objects.create(group=group, user=student, role="owner")
    client = client_for(student)
    url = f"/api/groups/{group.id}/messages/"
    for body in ({"body": "hello\x00"}, {"body": "hi", "extra\x00": 1}, {"body": "hi", "nested": [{"x": ["\x00"]}]}):
        response = client.post(url, body, format="json")
        assert response.status_code == 400, body
        assert response.data["detail"] == "The request contains a character that is not allowed."
    assert client.post(url, "body=hello%00", content_type="application/x-www-form-urlencoded").status_code == 400
    assert client.post(url, {"body": "hello\x00"}, format="multipart").status_code == 400
    assert client.post("/api/auth/login/", {"identifier": "a\x00", "password": "x"}, format="json").status_code == 400
    assert not Message.objects.exists()
    # The same message without the NUL goes through, and so does the text "\u0000" itself.
    assert client.post(url, {"body": "hello \\u0000"}, format="json").status_code == 201
    response = client.get(f"/api/groups/{group.id}/messages/?after=%00", HTTP_ACCEPT_LANGUAGE="fr")
    assert response.status_code == 400
    assert response.json()["detail"] == "La requête contient un caractère non autorisé."


def test_deeply_nested_json_is_checked_without_a_crash(client_for, student):
    client = client_for(student)
    client.raise_request_exception = False
    nested = "[" * 500 + '"\\u0000"' + "]" * 500  # deeply nested, with a NUL at the bottom
    response = client.patch("/api/auth/me/", data='{"first_name": "A", "x": ' + nested + "}", content_type="application/json")
    assert response.status_code == 400
    response = client.patch(
        "/api/auth/me/",
        data='{"first_name": "Aline", "x": ' + nested.replace("\\u0000", "") + "}",
        content_type="application/json",
    )
    assert response.status_code == 200


def test_contains_nul_looks_everywhere():
    assert not contains_nul({"a": ["b", {"c": 1, "d": None}], "e": 2.5})
    assert contains_nul({"a": ["b", {"c": "\x00"}]})
    assert contains_nul({"a\x00": 1})
    assert contains_nul(QueryDict("a=1&a=%00"))  # every value of a repeated parameter, not only the last
    deep = ["\x00"]
    for _ in range(20000):  # far deeper than recursion could go
        deep = [deep]
    assert contains_nul(deep)
