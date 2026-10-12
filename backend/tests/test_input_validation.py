"""Every view checks its input: malformed ids, query strings and bodies are a 400 (or 403/404), never a 500."""

import pytest

from apps.accounts.models import User
from apps.classroom.models import Classroom
from apps.community.models import GroupMembership, Message, MessageReport, StudyGroup
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
JUNK_QUERY = (
    "?unit=abc&quiz=abc&classroom=abc&year=abc&page=abc&grade=%00&subject=..%2F&after=abc&scope=class"
    "&status=x&role=x&q=%27%3B--&lang=xx"
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
