import pytest

from apps.community.models import GroupMembership, MessageReport, StudyGroup

pytestmark = pytest.mark.django_db


@pytest.fixture
def group(student):
    group = StudyGroup.objects.create(name="Maths Squad", grade="S2", created_by=student)
    GroupMembership.objects.create(group=group, user=student, role="owner")
    return group


def test_create_group_makes_creator_owner(client_for, student):
    response = client_for(student).post("/api/groups/", {"name": "Chem club", "grade": "S2"}, format="json")
    assert response.status_code == 201
    assert response.data["is_member"] and response.data["join_code"]
    assert GroupMembership.objects.get(group_id=response.data["id"], user=student).role == "owner"
    student.refresh_from_db()
    assert student.badges.filter(badge__code="team-player").exists()


def test_messages_are_members_only(client_for, other_student, group):
    client = client_for(other_student)
    assert client.get(f"/api/groups/{group.id}/messages/").status_code == 403
    client.post(f"/api/groups/{group.id}/join/")
    assert client.post(f"/api/groups/{group.id}/messages/", {"body": "Hi!"}, format="json").status_code == 201
    messages = client.get(f"/api/groups/{group.id}/messages/").data
    assert messages[-1]["body"] == "Hi!"
    after = client.get(f"/api/groups/{group.id}/messages/?after={messages[-1]['id']}").data
    assert after == []


def test_private_groups_need_the_code(client_for, other_student, group):
    group.is_private = True
    group.save()
    client = client_for(other_student)
    assert client.get("/api/groups/").data["count"] == 0
    assert client.post(f"/api/groups/{group.id}/join/").status_code == 404
    assert client.post("/api/groups/join-by-code/", {"code": group.join_code}, format="json").status_code == 200


def test_report_and_moderate(client_for, student, other_student, admin_user, group):
    GroupMembership.objects.create(group=group, user=other_student)
    message = client_for(other_student).post(f"/api/groups/{group.id}/messages/", {"body": "rude"}, format="json").data

    assert (
        client_for(student).post(f"/api/messages/{message['id']}/report/", {"reason": "Rude"}, format="json").status_code == 201
    )
    queue = client_for(admin_user).get("/api/admin/moderation/").data
    assert queue[0]["message"]["body"] == "rude"

    client_for(admin_user).post(f"/api/admin/moderation/{queue[0]['id']}/resolve/", {"hide": True}, format="json")
    assert not MessageReport.objects.filter(resolved=False).exists()
    shown = client_for(student).get(f"/api/groups/{group.id}/messages/").data
    assert shown[-1]["body"] == "[message removed by a moderator]"


def test_only_moderators_hide_messages(client_for, student, other_student, group):
    GroupMembership.objects.create(group=group, user=other_student)
    message = client_for(student).post(f"/api/groups/{group.id}/messages/", {"body": "hello"}, format="json").data
    assert client_for(other_student).post(f"/api/messages/{message['id']}/hide/").status_code == 403
    assert client_for(student).post(f"/api/messages/{message['id']}/hide/").status_code == 200  # owner


def test_ownership_passes_on_when_owner_leaves(client_for, student, other_student, group):
    GroupMembership.objects.create(group=group, user=other_student)
    client_for(student).post(f"/api/groups/{group.id}/leave/")
    assert GroupMembership.objects.get(group=group, user=other_student).role == "owner"


def test_shared_notes(client_for, student, group):
    client = client_for(student)
    assert (
        client.post(f"/api/groups/{group.id}/notes/", {"title": "Formulae", "body": "$v = d/t$"}, format="json").status_code
        == 201
    )
    assert client.get(f"/api/groups/{group.id}/notes/").data[0]["title"] == "Formulae"


def test_group_is_full(client_for, other_student, group):
    group.max_members = 1
    group.save()
    assert client_for(other_student).post(f"/api/groups/{group.id}/join/").status_code == 400


def test_empty_message_rejected(client_for, student, group):
    assert client_for(student).post(f"/api/groups/{group.id}/messages/", {"body": "   "}, format="json").status_code == 400
