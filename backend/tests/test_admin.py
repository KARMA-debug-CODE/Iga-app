import pytest

from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db


def test_admin_endpoints_are_admin_only(client_for, student, teacher):
    for user in (student, teacher):
        client = client_for(user)
        for url in (
            "/api/admin/stats/",
            "/api/admin/users/",
            "/api/admin/audit/",
            "/api/admin/review/",
            "/api/admin/moderation/",
        ):
            assert client.get(url).status_code == 403, (user.username, url)


def test_admin_approves_teacher_and_change_is_audited(client_for, admin_user):
    from .conftest import make_user

    pending = make_user("newteacher", role="teacher")
    client = client_for(admin_user)
    listed = client.get("/api/admin/users/?pending_teachers=1").data["results"]
    assert [u["username"] for u in listed] == ["newteacher"]
    assert client.patch(f"/api/admin/users/{pending.id}/", {"teacher_approved": True}, format="json").status_code == 200
    pending.refresh_from_db()
    assert pending.teacher_approved
    entry = AuditLog.objects.get(action="update_user")
    assert entry.actor == admin_user and entry.details["teacher_approved"] == ["False", "True"]


def test_admin_cannot_demote_themselves(client_for, admin_user):
    response = client_for(admin_user).patch(f"/api/admin/users/{admin_user.id}/", {"role": "student"}, format="json")
    assert response.status_code == 400


def test_stats(client_for, admin_user, student):
    data = client_for(admin_user).get("/api/admin/stats/").data
    assert data["users_by_role"]["student"] == 1


def test_dashboards(client_for, student, teacher):
    student_data = client_for(student).get("/api/dashboard/").data
    assert "assignments" in student_data and student_data["level"]["level"] == 1
    teacher_data = client_for(teacher).get("/api/dashboard/").data
    assert teacher_data["teacher"]["approved"] is True


def test_health_and_meta_are_public(client_for):
    assert client_for().get("/api/health/").data == {"status": "ok"}
    assert len(client_for().get("/api/meta/").data["grades"]) == 6
