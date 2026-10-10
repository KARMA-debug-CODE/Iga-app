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
    messages = client.get(f"/api/groups/{group.id}/messages/").data["messages"]
    assert messages[-1]["body"] == "Hi!"
    after = client.get(f"/api/groups/{group.id}/messages/?after={messages[-1]['id']}").data
    assert after == {"messages": [], "hidden_ids": []}


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
    assert shown["messages"][-1]["body"] == "[message removed by a moderator]"
    # Clients already showing the message learn it was hidden from their next poll.
    poll = client_for(student).get(f"/api/groups/{group.id}/messages/?after={message['id']}").data
    assert poll["hidden_ids"] == [message["id"]]


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


def test_last_member_leaving_deletes_the_group(client_for, student, group):
    client_for(student).post(f"/api/groups/{group.id}/leave/")
    assert not type(group).objects.filter(pk=group.pk).exists()


def test_only_the_owner_edits_the_group(client_for, student, teacher, group):
    GroupMembership.objects.create(group=group, user=teacher)
    assert client_for(teacher).patch(f"/api/groups/{group.id}/", {"name": "Mine now"}, format="json").status_code == 403
    assert client_for(student).patch(f"/api/groups/{group.id}/", {"name": "Renamed"}, format="json").status_code == 200


def test_members_see_short_names_and_real_roles(client_for, student, other_student, group):
    from .conftest import make_user

    pending = make_user("pretend", role="teacher", first_name="Paul", last_name="Kagame")  # not approved
    for user in (other_student, pending):
        GroupMembership.objects.create(group=group, user=user)
    client_for(pending).post(f"/api/groups/{group.id}/messages/", {"body": "I am your teacher"}, format="json")
    members = {m["id"]: m for m in client_for(other_student).get(f"/api/groups/{group.id}/").data["members"]}
    assert members[student.id]["display_name"] == "Aline U."
    assert members[pending.id]["role"] == "student"  # no teacher badge until approved
    assert "xp" not in members[student.id] and "username" not in members[student.id]
    message = client_for(other_student).get(f"/api/groups/{group.id}/messages/").data["messages"][-1]
    assert message["author"] == {"id": pending.id, "name": "Paul K.", "role": "student", "avatar": {}}


def test_join_codes_are_rate_limited(client_for, other_student, group, monkeypatch):
    from rest_framework.throttling import SimpleRateThrottle

    from .conftest import RELAXED_RATES

    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RELAXED_RATES, "join": "3/min"})
    client = client_for(other_student)
    for _ in range(3):
        client.post("/api/groups/join-by-code/", {"code": "WRONG1"}, format="json")
    assert client.post("/api/groups/join-by-code/", {"code": group.join_code}, format="json").status_code == 429
    assert client.post("/api/classes/join/", {"code": "WRONG1"}, format="json").status_code == 429
