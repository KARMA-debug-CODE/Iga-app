"""The profile drives the whole app: changing grade moves the student's classes, lessons and practice with
them; avatars are chosen from fixed options."""

import pytest

from apps.classroom.models import Assignment, Classroom, Enrollment
from apps.curriculum.models import Lesson, LessonProgress, Unit

from .conftest import make_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def s2_class(teacher, subject):
    return Classroom.objects.create(name="S2 Maths", grade="S2", subject=subject, teacher=teacher)


@pytest.fixture
def s6_class(teacher, subject):
    return Classroom.objects.create(name="S6 Maths", grade="S6", subject=subject, teacher=teacher)


def test_changing_grade_moves_the_students_classes(client_for, student, teacher, s2_class, s6_class):
    Enrollment.objects.create(classroom=s2_class, student=student)
    Enrollment.objects.create(classroom=s6_class, student=student, active=False)
    Assignment.objects.create(classroom=s2_class, title="Old homework", created_by=teacher)
    client = client_for(student)
    assert [c["name"] for c in client.get("/api/classes/").data["results"]] == ["S2 Maths"]

    response = client.patch("/api/auth/me/", {"grade": "S6"}, format="json")
    assert response.status_code == 200
    assert response.data["grade"] == "S6" and response.data["left_classes"] == ["S2 Maths"]

    # The student's lists follow S6; the S2 class is under "previous classes", still readable.
    assert [c["name"] for c in client.get("/api/classes/").data["results"]] == ["S6 Maths"]
    assert [c["name"] for c in client.get("/api/classes/", {"previous": 1}).data["results"]] == ["S2 Maths"]
    assert client.get(f"/api/classes/{s2_class.id}/").data["previous"] is True
    assert client.get(f"/api/classes/{s6_class.id}/").data["previous"] is False
    assert client.get("/api/assignments/").data["results"] == []
    assert client.get("/api/dashboard/").data["assignments"] == []

    # The teacher keeps the student and their results, marked as moved.
    roster = client_for(teacher).get(f"/api/classes/{s2_class.id}/").data["students"]
    assert [(s["username"], s["moved_to"]) for s in roster] == [("student", "S6")]
    report = client_for(teacher).get(f"/api/classes/{s2_class.id}/report/").data
    assert report["rows"][0]["moved_to"] == "S6"
    assert client_for(teacher).get("/api/classes/").data["results"][0]["student_count"] in (0, 1)

    # Moving back brings the S2 class back.
    client.patch("/api/auth/me/", {"grade": "S2"}, format="json")
    assert [c["name"] for c in client.get("/api/classes/").data["results"]] == ["S2 Maths"]


def test_joining_a_class_again_makes_it_active(client_for, student, s6_class):
    Enrollment.objects.create(classroom=s6_class, student=student, active=False)
    client_for(student).post("/api/classes/join/", {"code": s6_class.join_code}, format="json")
    assert Enrollment.objects.get(classroom=s6_class, student=student).active


def test_continue_learning_follows_the_new_grade(client_for, student, subject):
    s2 = Unit.objects.create(subject=subject, grade="S2", number=1, title="S2 unit")
    s6 = Unit.objects.create(subject=subject, grade="S6", number=1, title="S6 unit")
    done = Lesson.objects.create(unit=s2, slug="s2-a", title="S2 A", status="published", is_free=True, order=1)
    Lesson.objects.create(unit=s2, slug="s2-b", title="S2 B", status="published", is_free=True, order=2)
    Lesson.objects.create(unit=s6, slug="s6-a", title="S6 A", status="published", is_free=True, order=1)
    LessonProgress.objects.create(user=student, lesson=done)
    client = client_for(student)
    assert client.get("/api/dashboard/").data["continue_learning"]["slug"] == "s2-b"
    client.patch("/api/auth/me/", {"grade": "S6"}, format="json")
    assert client.get("/api/dashboard/").data["continue_learning"]["slug"] == "s6-a"


def test_avatars_are_chosen_from_the_options(client_for, student):
    client = client_for(student)
    ok = client.patch("/api/auth/me/", {"avatar": {"skin": 3, "hair": 4, "bg": 9}}, format="json")
    assert ok.status_code == 200 and ok.data["avatar"] == {"skin": 3, "hair": 4, "bg": 9}
    for bad in ({"skin": 99}, {"hat": 1}, {"skin": "3"}, {"skin": True}, ["skin"], "a.png"):
        assert client.patch("/api/auth/me/", {"avatar": bad}, format="json").status_code == 400
    student.refresh_from_db()
    assert student.avatar == {"skin": 3, "hair": 4, "bg": 9}


def test_other_students_see_avatars_in_the_leaderboard(client_for, student):
    student.avatar = {"skin": 1}
    student.xp = 50
    student.save()
    friend = make_user("friend", grade="S2")
    entries = client_for(friend).get("/api/leaderboard/", {"period": "all"}).data["entries"]
    assert [(e["name"], e["avatar"]) for e in entries] == [(student.short_name, {"skin": 1})]
