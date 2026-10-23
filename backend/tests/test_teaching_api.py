"""Teaching Packs API: the class's own teacher, paid schools only (apps/teaching/views.py)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.classroom.models import Classroom
from apps.curriculum.models import Lesson, Subject, Unit
from apps.teaching.models import TeachingPack
from apps.teaching.views import PackViewSet

from .conftest import add_mcq, make_school, make_user
from .teaching_factories import class_with_students, mark_answer

PACKS = "/api/teaching/packs/"


@pytest.fixture
def classroom(teacher, subject):
    c, _students = class_with_students(teacher, subject, 5)
    return c


def make_pack(client_for, teacher, classroom, unit, **extra):
    response = client_for(teacher).post(PACKS, {"classroom": classroom.id, "unit": unit.id, **extra}, format="json")
    assert response.status_code == 201, response.content
    return response.json()


def teacher_in(school):
    return make_user(f"t-{school.name}", role=User.Role.TEACHER, teacher_approved=True, school=school)


def test_creating_a_pack_saves_and_returns_it(client_for, teacher, unit, lesson, classroom):
    data = make_pack(client_for, teacher, classroom, unit)
    pack = TeachingPack.objects.get(pk=data["id"])
    assert pack.created_by == teacher and pack.classroom == classroom and pack.lesson == lesson
    assert data["document"]["unit"]["id"] == unit.id and data["ai_used"] is False
    assert (data["classroom"], data["unit_id"], data["lesson_id"]) == (classroom.id, unit.id, lesson.id)
    assert data["assignments"] == [] and data["students_needing_help"] == []


def test_units_are_listed_weakest_first(client_for, teacher, subject, unit):
    c, students = class_with_students(teacher, subject, 5, prefix="u")
    strong = Unit.objects.create(subject=subject, grade="S2", number=2, title="Angles")
    untouched = Unit.objects.create(subject=subject, grade="S2", number=3, title="Triangles")
    weak_q, strong_q = add_mcq(subject, unit), add_mcq(subject, strong, "angle?")
    for student in students:
        mark_answer(student, weak_q, 0, choices=["3"])
        mark_answer(student, strong_q, 1, choices=["4"])
    rows = client_for(teacher).get(f"/api/teaching/classes/{c.id}/units/").json()
    assert [r["unit_id"] for r in rows] == [unit.id, strong.id, untouched.id]
    assert (rows[0]["average"], rows[0]["answered"], rows[0]["misconceptions_found"]) == (0.0, 5, 1)
    assert (rows[2]["average"], rows[2]["answered"], rows[2]["misconceptions_found"]) == (None, 0, 0)
    assert rows[0]["label"] == "S2 Unit 1: Linear graphs" and rows[0]["subject"] == "Mathematics"


def test_a_class_without_a_subject_lists_every_subject(client_for, teacher, unit):
    physics = Subject.objects.create(code="physics", name="Physics", name_fr="Physique")
    motion = Unit.objects.create(subject=physics, grade="S2", number=1, title="Motion")
    Unit.objects.create(subject=physics, grade="S3", number=1, title="Not this grade")
    c = Classroom.objects.create(name="Homeroom", grade="S2", teacher=teacher)
    rows = client_for(teacher).get(f"/api/teaching/classes/{c.id}/units/").json()
    assert {r["unit_id"] for r in rows} == {unit.id, motion.id}


def test_the_lesson_must_belong_to_the_unit(client_for, teacher, subject, unit, classroom):
    other_unit = Unit.objects.create(subject=subject, grade="S2", number=2, title="Angles")
    stray = Lesson.objects.create(unit=other_unit, slug="stray", title="Stray", body="x", status="published")
    response = client_for(teacher).post(PACKS, {"classroom": classroom.id, "unit": unit.id, "lesson": stray.id}, format="json")
    assert response.status_code == 400


def test_the_unit_must_match_the_class(client_for, teacher, subject, classroom):
    s3 = Unit.objects.create(subject=subject, grade="S3", number=1, title="Older")
    physics = Subject.objects.create(code="physics", name="Physics", name_fr="Physique")
    other_subject = Unit.objects.create(subject=physics, grade="S2", number=1, title="Motion")
    for wrong in (s3, other_subject):
        response = client_for(teacher).post(PACKS, {"classroom": classroom.id, "unit": wrong.id}, format="json")
        assert response.status_code == 400, wrong


def test_unpaid_school_gets_the_teaser(client_for, subject, unit):
    unpaid_teacher = teacher_in(make_school("Unpaid", paid_until=None))
    c, students = class_with_students(unpaid_teacher, subject, 5, prefix="free")
    question = add_mcq(subject, unit)
    for student in students:
        mark_answer(student, question, 0, choices=["3"])
    response = client_for(unpaid_teacher).post(PACKS, {"classroom": c.id, "unit": unit.id}, format="json")
    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "subscription_required"
    assert body["teaser"] == {"unit": "S2 Unit 1: Linear graphs", "average": 0.0, "misconceptions_found": 1}
    assert client_for(unpaid_teacher).get(f"/api/teaching/classes/{c.id}/units/").status_code == 200
    assert not TeachingPack.objects.exists()


def test_a_school_in_its_grace_period_can_make_packs(client_for, subject, unit):
    grace_teacher = teacher_in(make_school("Grace", paid_until=timezone.now() - timedelta(days=1)))
    c, _students = class_with_students(grace_teacher, subject, 1, prefix="grace")
    make_pack(client_for, grace_teacher, c, unit)


def test_lapsed_school_keeps_its_packs(client_for, subject, unit):
    school = make_school("Lapsing", paid_until=timezone.now() + timedelta(days=10))
    lapsed_teacher = teacher_in(school)
    c, _students = class_with_students(lapsed_teacher, subject, 1, prefix="lapse")
    pack_id = make_pack(client_for, lapsed_teacher, c, unit)["id"]
    school.paid_until = timezone.now() - timedelta(days=60)
    school.save()
    # A later request loads the user afresh (access is cached on the user object for one request).
    client = client_for(User.objects.get(pk=lapsed_teacher.pk))
    assert client.get(f"{PACKS}{pack_id}/").status_code == 200
    assert client.patch(f"{PACKS}{pack_id}/", {"plan": {"objective": "Still mine"}}, format="json").status_code == 200
    assert client.post(PACKS, {"classroom": c.id, "unit": unit.id}, format="json").status_code == 403
    assert client.delete(f"{PACKS}{pack_id}/").status_code == 204


def test_archived_class_refuses_new_packs(client_for, teacher, unit, classroom):
    pack_id = make_pack(client_for, teacher, classroom, unit)["id"]
    classroom.archived = True
    classroom.save()
    response = client_for(teacher).post(PACKS, {"classroom": classroom.id, "unit": unit.id}, format="json")
    assert response.status_code == 400 and response.json()["code"] == "class_archived"
    assert client_for(teacher).get(f"{PACKS}{pack_id}/").status_code == 200


def test_plan_edits_are_allow_listed_cleaned_and_merged(client_for, teacher, unit, classroom):
    pack_id = make_pack(client_for, teacher, classroom, unit)["id"]
    client, url = client_for(teacher), f"{PACKS}{pack_id}/"
    response = client.patch(url, {"plan": {"objective": "New ​goal", "steps": [{"teacher": "Mine"}]}}, format="json")
    assert response.status_code == 200
    plan = client.get(url).json()["document"]["plan"]
    assert plan["objective"] == "New goal"
    assert plan["steps"][0]["teacher"] == "Mine" and plan["steps"][0]["minutes"] == 5
    assert TeachingPack.objects.get(pk=pack_id).plan_edits["objective"] == "New goal"
    assert client.patch(url, {"plan": {"nonsense": "x"}}, format="json").status_code == 400
    assert client.patch(url, {"plan": {"objective": "x" * 2001}}, format="json").status_code == 400
    assert client.patch(url, {"plan": {"steps": [{"minutes": 99}]}}, format="json").status_code == 400


def test_students_needing_help_are_live_not_stored(client_for, teacher, subject, unit):
    c, students = class_with_students(teacher, subject, 5, prefix="h")
    for i in range(3):
        mark_answer(students[0], add_mcq(subject, unit, f"q{i}?"), 0)
    data = make_pack(client_for, teacher, c, unit)
    assert [s["id"] for s in data["students_needing_help"]] == [students[0].id]
    assert "students_needing_help" not in TeachingPack.objects.get(pk=data["id"]).document


def test_packs_follow_the_class_when_it_changes_teacher(client_for, teacher, other_teacher, unit, classroom):
    pack_id = make_pack(client_for, teacher, classroom, unit)["id"]
    classroom.teacher = other_teacher
    classroom.save()
    assert client_for(teacher).get(f"{PACKS}{pack_id}/").status_code == 404
    assert client_for(other_teacher).get(f"{PACKS}{pack_id}/").status_code == 200


def test_list_filters_by_class(client_for, teacher, subject, unit, classroom):
    other, _students = class_with_students(teacher, subject, 1, prefix="second")
    first = make_pack(client_for, teacher, classroom, unit)["id"]
    make_pack(client_for, teacher, other, unit)
    client = client_for(teacher)
    listed = client.get(PACKS, {"classroom": classroom.id}).json()
    rows = listed["results"] if isinstance(listed, dict) else listed
    assert [r["id"] for r in rows] == [first]
    assert set(rows[0]) == {"id", "classroom", "classroom_name", "unit_label", "lesson_title", "created_at", "ai_used"}
    assert client.get(PACKS, {"classroom": "abc"}).status_code == 400


def test_creation_uses_the_teaching_pack_throttle():
    view = PackViewSet()
    view.action = "create"
    view.get_throttles()
    assert view.throttle_scope == "teaching_pack"
    listing = PackViewSet()
    listing.action = "list"
    listing.get_throttles()
    assert getattr(listing, "throttle_scope", None) is None
