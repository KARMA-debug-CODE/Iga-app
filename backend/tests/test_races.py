"""Two requests on the same record: no lost updates, no stale powers, one decision at a time.

The first tests replay the interleaving deterministically (a request that read a row before someone
else changed it). The threaded ones run real simultaneous requests and need PostgreSQL (SQLite has
no row locks); CI runs them.
"""

import threading
import time
from datetime import timedelta

import pytest
from django.db import connection, connections, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.classroom.models import Classroom, Enrollment
from apps.community.models import GroupMembership, StudyGroup
from apps.schools.models import School

from .conftest import make_school, make_user

PASSWORD = "Str0ng-pass-123"


@pytest.fixture
def lycee(db):
    return make_school("Lycee", "Gasabo", paid_until=timezone.now() + timedelta(days=10))


@pytest.mark.django_db
def test_a_contact_edit_does_not_undo_a_payment(client_for, lycee):
    admin = make_user("lkadmin", role=User.Role.SCHOOL_ADMIN, school=lycee)
    client = client_for(admin)
    assert admin.school.paid_until  # the request's copy of the school, read before the payment lands
    paid = timezone.now() + timedelta(days=120)
    School.objects.filter(pk=lycee.pk).update(paid_until=paid)  # a payment is applied meanwhile
    assert client.patch("/api/school/", {"phone": "+250 788 123 456"}, format="json").status_code == 200
    lycee.refresh_from_db()
    assert lycee.paid_until == paid and lycee.phone == "+250 788 123 456"


@pytest.mark.django_db
def test_a_profile_edit_does_not_undo_decisions_made_meanwhile(client_for, lycee):
    teacher = make_user("tina", role=User.Role.TEACHER, teacher_approved=True, school=lycee)
    client = client_for(teacher)  # this request read the account before the changes below
    User.objects.filter(pk=teacher.pk).update(teacher_approved=False, teacher_revoked=True, school_status="rejected")
    User.objects.filter(pk=teacher.pk).update(password="argon2$changed-by-a-reset")
    assert client.patch("/api/auth/me/", {"first_name": "Tina"}, format="json").status_code == 200
    fresh = User.objects.get(pk=teacher.pk)
    assert (fresh.first_name, fresh.teacher_approved, fresh.teacher_revoked, fresh.school_status) == (
        "Tina",
        False,
        True,
        "rejected",
    )
    assert fresh.password == "argon2$changed-by-a-reset"


@pytest.mark.django_db
def test_a_removed_school_admin_cannot_act_on_a_request_already_on_its_way(client_for, lycee):
    first = make_user("first", role=User.Role.SCHOOL_ADMIN, school=lycee)
    second = make_user("second", role=User.Role.SCHOOL_ADMIN, school=lycee)
    pupil = make_user("pupil", school=None)
    pupil.school, pupil.school_status = lycee, User.SchoolStatus.PENDING
    pupil.save()
    stale_second = client_for(second)  # second's request was authenticated before being removed
    assert client_for(first).post(f"/api/school/members/{second.id}/remove/").status_code == 204
    assert stale_second.post(f"/api/school/members/{first.id}/remove/").status_code == 403
    assert (
        stale_second.post("/api/school/members/decide/", {"ids": [pupil.id], "approve": True}, format="json").status_code == 403
    )
    first.refresh_from_db()
    pupil.refresh_from_db()
    assert first.school_id == lycee.id and pupil.school_status == User.SchoolStatus.PENDING


@pytest.mark.django_db
def test_a_moved_students_password_cannot_be_reset_by_the_old_teacher(client_for, teacher, student):
    old_class = Classroom.objects.create(name="S2 A", grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=old_class, student=student, active=False)  # moved to another grade
    response = client_for(teacher).post(f"/api/classes/{old_class.id}/reset_password/", {"student": student.id}, format="json")
    assert response.status_code == 400
    student.refresh_from_db()
    assert student.check_password(PASSWORD) and not student.must_change_password


# --- Real concurrency (PostgreSQL) ----------------------------------------------------------------


def _postgres_only():
    if connection.vendor != "postgresql":
        pytest.skip("row locks need PostgreSQL")


def _run_together(functions):
    """Run the functions in threads released at the same moment; return their results (or exceptions)."""
    barrier = threading.Barrier(len(functions))
    results = [None] * len(functions)

    def worker(i, fn):
        try:
            barrier.wait()
            results[i] = fn()
        except Exception as exc:  # noqa: BLE001  (the test inspects it)
            results[i] = exc
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker, args=(i, fn)) for i, fn in enumerate(functions)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    return results


@pytest.mark.django_db(transaction=True)
def test_group_leave_waits_for_the_group_lock(client_for):
    _postgres_only()
    owner, second, third = (make_user(name) for name in ("owner", "second", "third"))
    group = StudyGroup.objects.create(name="G")
    GroupMembership.objects.create(group=group, user=owner, role=GroupMembership.Role.OWNER)
    GroupMembership.objects.create(group=group, user=second)
    GroupMembership.objects.create(group=group, user=third)
    released = threading.Event()
    finished = {}

    def hold_lock():
        with transaction.atomic():
            StudyGroup.objects.select_for_update().get(pk=group.pk)
            time.sleep(0.5)
            finished["holder"] = time.monotonic()
        released.set()

    def leave():
        response = client_for(owner).post(f"/api/groups/{group.id}/leave/")
        finished["leave"] = time.monotonic()
        return response.status_code

    results = _run_together([hold_lock, leave])
    assert results[1] == 204
    assert finished["leave"] >= finished["holder"]  # it waited for the other transaction
    owners = list(GroupMembership.objects.filter(group=group, role=GroupMembership.Role.OWNER).values_list("user_id", flat=True))
    assert owners == [second.id]


@pytest.mark.django_db(transaction=True)
def test_owner_and_successor_leaving_together_leave_one_owner(client_for):
    _postgres_only()
    for round_ in range(3):
        StudyGroup.objects.all().delete()
        users = [make_user(f"u{round_}{n}") for n in range(3)]
        group = StudyGroup.objects.create(name="G")
        for n, user in enumerate(users):
            GroupMembership.objects.create(group=group, user=user, role="owner" if n == 0 else "member")
        url = f"/api/groups/{group.id}/leave/"
        results = _run_together([lambda u=u, url=url: client_for(u).post(url).status_code for u in users[:2]])
        assert results == [204, 204], results
        remaining = list(GroupMembership.objects.filter(group=group).values_list("user_id", "role"))
        assert remaining == [(users[2].id, "owner")]
        User.objects.filter(pk__in=[u.pk for u in users]).delete()


@pytest.mark.django_db(transaction=True)
def test_a_full_group_never_overfills(client_for):
    _postgres_only()
    owner = make_user("owner")
    group = StudyGroup.objects.create(name="G", max_members=3)
    GroupMembership.objects.create(group=group, user=owner, role="owner")
    joiners = [make_user(f"joiner{n}") for n in range(5)]
    results = _run_together([lambda u=u: client_for(u).post(f"/api/groups/{group.id}/join/").status_code for u in joiners])
    assert sorted(results) == [200, 200, 400, 400, 400], results
    assert GroupMembership.objects.filter(group=group).count() == 3


@pytest.mark.django_db(transaction=True)
def test_joining_a_class_twice_at_once_makes_one_enrolment(client_for):
    _postgres_only()
    teacher = make_user("teach", role=User.Role.TEACHER, teacher_approved=True)
    student = make_user("pupil")
    classroom = Classroom.objects.create(name="S2", grade="S2", teacher=teacher)
    results = _run_together(
        [lambda: client_for(student).post("/api/classes/join/", {"code": classroom.join_code}, format="json").status_code] * 3
    )
    assert results == [200, 200, 200], results
    assert Enrollment.objects.filter(classroom=classroom, student=student).count() == 1


@pytest.mark.django_db(transaction=True)
def test_two_school_admins_removing_each_other_leave_one(client_for):
    _postgres_only()
    school = make_school("Lycee", "Gasabo")
    first = make_user("first", role=User.Role.SCHOOL_ADMIN, school=school)
    second = make_user("second", role=User.Role.SCHOOL_ADMIN, school=school)
    results = _run_together(
        [
            lambda: client_for(first).post(f"/api/school/members/{second.id}/remove/").status_code,
            lambda: client_for(second).post(f"/api/school/members/{first.id}/remove/").status_code,
        ]
    )
    assert sorted(results) == [204, 403], results
    still = User.objects.filter(pk__in=[first.pk, second.pk], school=school).count()
    assert still == 1
