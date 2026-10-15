from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import ParentInvite, ParentLink, User, parent_code_digest
from apps.community.models import GroupMembership, StudyGroup
from apps.curriculum.models import LessonProgress

from .conftest import make_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def parent(db):
    return make_user("mama", role=User.Role.PARENT, first_name="Mama")


def link(client_for, student, parent):
    code = client_for(student).post("/api/auth/parent-code/").data["code"]
    return client_for(parent).post("/api/children/", {"code": code}, format="json")


def test_parent_can_register_without_grade(client_for):
    response = client_for().post(
        "/api/auth/register/",
        {"username": "papa", "password": "Str0ng-pass-123", "first_name": "Papa", "role": "parent", "grade": "S3"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["user"]["role"] == "parent"
    assert response.data["user"]["grade"] == ""


def test_link_with_code_and_see_progress(client_for, student, parent, lesson):
    LessonProgress.objects.create(user=student, lesson=lesson)
    response = link(client_for, student, parent)
    assert response.status_code == 201
    assert response.data["name"] == "Aline Uwase"
    assert response.data["lessons_this_week"] == 1

    children = client_for(parent).get("/api/children/").data
    assert [c["id"] for c in children] == [student.id]
    report = client_for(parent).get(f"/api/children/{student.id}/").data
    maths = next(s for s in report["subjects"] if s["code"] == "mathematics")
    assert maths["completed"] == 1 and maths["lessons"] == 1


def test_codes_are_single_use_and_expire(client_for, student, parent):
    code = client_for(student).post("/api/auth/parent-code/").data["code"]
    assert client_for(parent).post("/api/children/", {"code": code}, format="json").status_code == 201
    other = make_user("baba", role=User.Role.PARENT)
    assert client_for(other).post("/api/children/", {"code": code}, format="json").status_code == 400

    fresh = client_for(student).post("/api/auth/parent-code/").data["code"]
    ParentInvite.objects.filter(code_hash=parent_code_digest(fresh)).update(expires_at=timezone.now() - timedelta(minutes=1))
    assert client_for(other).post("/api/children/", {"code": fresh}, format="json").status_code == 400


def test_new_code_replaces_unused_one(client_for, student, parent):
    first = client_for(student).post("/api/auth/parent-code/").data["code"]
    client_for(student).post("/api/auth/parent-code/")
    assert client_for(parent).post("/api/children/", {"code": first}, format="json").status_code == 400


def test_parents_only_see_linked_children(client_for, student, other_student, parent):
    link(client_for, student, parent)
    assert client_for(parent).get(f"/api/children/{other_student.id}/").status_code == 404


def test_roles_are_enforced(client_for, student, parent, teacher):
    assert client_for(parent).post("/api/auth/parent-code/").status_code == 403
    assert client_for(teacher).post("/api/auth/parent-code/").status_code == 403
    assert client_for(student).get("/api/children/").status_code == 403


def test_student_can_see_and_remove_parent(client_for, student, parent):
    link(client_for, student, parent)
    parents = client_for(student).get("/api/auth/parents/").data
    assert parents[0]["id"] == parent.id
    assert client_for(student).delete(f"/api/auth/parents/{parent.id}/").status_code == 204
    assert not ParentLink.objects.exists()
    assert client_for(parent).get(f"/api/children/{student.id}/").status_code == 404


def test_parent_can_unlink(client_for, student, parent):
    link(client_for, student, parent)
    assert client_for(parent).delete(f"/api/children/{student.id}/").status_code == 204
    assert client_for(parent).get("/api/children/").data == []


def test_parents_are_kept_out_of_study_groups_and_leaderboards(client_for, student, parent):
    group = StudyGroup.objects.create(name="Squad", grade="S2", created_by=student)
    GroupMembership.objects.create(group=group, user=student, role="owner")
    client = client_for(parent)
    assert client.get("/api/groups/").status_code == 403
    assert client.post(f"/api/groups/{group.id}/join/").status_code == 403
    assert client.get("/api/leaderboard/").data["entries"] == []
