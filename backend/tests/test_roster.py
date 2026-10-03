import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.classroom.models import Classroom, Enrollment
from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db

CSV = """First name,Last name,Username,Email
Aline,Uwase,,
Éric,Niyonzima,,eric@example.com
Divine,Ishimwe,divine.i,
"""


@pytest.fixture
def classroom(teacher, subject):
    return Classroom.objects.create(name="S2 Maths", grade="S2", subject=subject, teacher=teacher)


def post(client, classroom, text, confirm=False):
    return client.post(f"/api/classes/{classroom.id}/import_roster/", {"csv": text, "confirm": confirm}, format="json")


def test_preview_then_create_accounts(client_for, teacher, classroom):
    client = client_for(teacher)
    preview = post(client, classroom, CSV)
    assert preview.status_code == 200 and preview.data["valid"]
    assert [r["username"] for r in preview.data["rows"]] == ["aline.uwase", "eric.niyonzima", "divine.i"]
    assert not User.objects.filter(username="aline.uwase").exists()  # preview creates nothing

    created = post(client, classroom, CSV, confirm=True)
    assert created.status_code == 201
    rows = created.data["created"]
    assert len(rows) == 3 and all(r["temporary_password"] for r in rows)
    aline = User.objects.get(username="aline.uwase")
    assert aline.is_student and aline.grade == "S2" and aline.must_change_password
    assert aline.check_password(rows[0]["temporary_password"])
    assert Enrollment.objects.filter(classroom=classroom).count() == 3
    assert AuditLog.objects.filter(action="import_roster").exists()


def test_problems_block_the_whole_import(client_for, teacher, classroom, student):
    text = "first_name,last_name,username\nAline,U,student\n,NoFirst,\nBob,B,bob\nBob,C,BOB\n"
    response = post(client_for(teacher), classroom, text, confirm=True)
    assert response.status_code == 200 and not response.data["valid"]
    errors = {r["line"]: r["errors"] for r in response.data["rows"]}
    assert "already taken" in errors[2][0]
    assert "First name is missing." in errors[3]
    assert "appears twice" in " ".join(errors[5])
    assert not User.objects.filter(username="bob").exists()


def test_generated_usernames_avoid_existing_ones(client_for, teacher, classroom):
    User.objects.create_user(username="aline.uwase", password="x" * 12)
    text = "name\nAline Uwase\nAline Uwase\n"
    rows = post(client_for(teacher), classroom, text).data["rows"]
    assert [r["username"] for r in rows] == ["aline.uwase2", "aline.uwase3"]


def test_limits_and_permissions(client_for, teacher, other_teacher, student, classroom):
    big = "first_name\n" + "\n".join(f"Kid{i}" for i in range(201))
    assert post(client_for(teacher), classroom, big).status_code == 400
    assert post(client_for(teacher), classroom, "username\nx\n").status_code == 400  # no name column
    assert post(client_for(other_teacher), classroom, CSV).status_code == 404
    assert post(client_for(student), classroom, CSV).status_code == 403


def test_temporary_password_must_be_changed_first(client_for, teacher, classroom):
    created = post(client_for(teacher), classroom, CSV, confirm=True).data["created"][0]
    client = APIClient()
    login = client.post(
        "/api/auth/login/", {"identifier": created["username"], "password": created["temporary_password"]}, format="json"
    )
    assert login.status_code == 200 and login.data["user"]["must_change_password"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    blocked = client.get("/api/dashboard/")
    assert blocked.status_code == 403 and blocked.data["detail"].code == "password_change_required"
    assert client.get("/api/auth/me/").status_code == 200

    same = client.post(
        "/api/auth/password/",
        {"current_password": created["temporary_password"], "new_password": created["temporary_password"]},
        format="json",
    )
    assert same.status_code == 400
    changed = client.post(
        "/api/auth/password/",
        {"current_password": created["temporary_password"], "new_password": "My-own-pass-2026"},
        format="json",
    )
    assert changed.status_code == 200
    assert client.get("/api/dashboard/").status_code == 200


def test_teacher_resets_a_forgotten_password(client_for, teacher, other_teacher, student, classroom):
    Enrollment.objects.create(classroom=classroom, student=student)
    assert (
        client_for(other_teacher).post(f"/api/classes/{classroom.id}/reset_password/", {"student": student.id}).status_code == 404
    )
    response = client_for(teacher).post(f"/api/classes/{classroom.id}/reset_password/", {"student": student.id}, format="json")
    assert response.status_code == 200
    student.refresh_from_db()
    assert student.must_change_password and student.check_password(response.data["temporary_password"])
    assert AuditLog.objects.filter(action="reset_student_password").exists()

    outsider = User.objects.create_user(username="outsider", password="x" * 12, role="student")
    response = client_for(teacher).post(f"/api/classes/{classroom.id}/reset_password/", {"student": outsider.id}, format="json")
    assert response.status_code == 400
