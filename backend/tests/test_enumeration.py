"""No answer reveals whether an account exists (S10): messages, status codes and the work done."""

import pyotp
import pytest
from rest_framework.test import APIClient

from apps.accounts.hashers import IgaArgon2PasswordHasher
from apps.accounts.models import User
from apps.classroom.models import Classroom
from apps.core.models import AuditLog

from .conftest import make_user

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"


def login(identifier, password="Wrong-pass-999", **extra):
    return APIClient().post("/api/auth/login/", {"identifier": identifier, "password": password, **extra}, format="json")


@pytest.fixture
def hashing(monkeypatch):
    """Counts password hashes created and checked."""
    counts = {"encode": 0, "verify": 0}
    real_encode, real_verify = IgaArgon2PasswordHasher.encode, IgaArgon2PasswordHasher.verify

    def encode(self, *args, **kwargs):
        counts["encode"] += 1
        return real_encode(self, *args, **kwargs)

    def verify(self, *args, **kwargs):
        counts["verify"] += 1
        return real_verify(self, *args, **kwargs)

    monkeypatch.setattr(IgaArgon2PasswordHasher, "encode", encode)
    monkeypatch.setattr(IgaArgon2PasswordHasher, "verify", verify)
    return counts


def test_login_answers_are_identical_for_real_and_made_up_accounts(student):
    real = [login("student"), login("student@example.com")]
    fake = [login("nobody"), login("nobody@example.com")]
    assert {(r.status_code, str(r.data)) for r in real} == {(f.status_code, str(f.data)) for f in fake}


def test_login_does_the_same_hashing_work_for_real_and_made_up_accounts(student, hashing):
    """One Argon2id check each way, and no new hash: timing can't tell the two apart."""
    login("nobody-at-all")  # builds the process's dummy hash once
    hashing.update(encode=0, verify=0)
    login("student")
    real = dict(hashing)
    hashing.update(encode=0, verify=0)
    login("nobody-else")
    assert real == dict(hashing) == {"encode": 0, "verify": 1}


def test_inactive_accounts_answer_like_a_wrong_password(student, hashing):
    User.objects.filter(pk=student.pk).update(is_active=False)
    response = login("student", PASSWORD)
    assert response.status_code == 401 and response.data == login("nobody").data


def test_the_2fa_step_only_appears_after_the_right_password(student):
    student.totp_secret = pyotp.random_base32()
    student.totp_enabled = True
    student.save()
    wrong = login("student", "Wrong-pass-999")
    assert wrong.status_code == 401 and "otp_required" not in wrong.data
    assert wrong.data == login("nobody").data


def register(email, username, ip="10.1.1.1"):
    payload = {"username": username, "email": email, "password": PASSWORD, "first_name": "N", "grade": "S1", "accept_terms": True}
    return APIClient().post("/api/auth/register/", payload, format="json", REMOTE_ADDR=ip)


def test_sign_up_can_test_only_a_few_emails_an_hour(student, settings):
    settings.EMAIL_IN_USE_LIMIT = 3
    for n in range(3):
        response = register("student@example.com", f"probe{n}")
        assert response.status_code == 400 and "email" in response.data
    # From now on every sign-up with an email is refused from this address, taken or not.
    assert register("student@example.com", "probe9").status_code == 429
    assert register("free-address@example.com", "probe10").status_code == 429
    assert AuditLog.objects.filter(action="email_in_use").exists()
    # Without an email, or from another address, sign-up still works.
    no_email = APIClient().post(
        "/api/auth/register/",
        {"username": "plainkid", "password": PASSWORD, "first_name": "P", "grade": "S1", "accept_terms": True},
        format="json",
        REMOTE_ADDR="10.1.1.1",
    )
    assert no_email.status_code == 201
    assert register("free-address@example.com", "elsewhere", ip="10.1.1.2").status_code == 201


def test_sign_up_messages_are_translated_and_point_to_recovery(student):
    response = register("STUDENT@example.com", "probe")
    assert "reset your password" in str(response.data["email"])


def test_profile_email_changes_need_the_password_and_are_budgeted(student, other_student, client_for, settings):
    settings.EMAIL_IN_USE_LIMIT = 2
    client = client_for(other_student)
    no_password = client.patch("/api/auth/me/", {"email": "fresh@example.com"}, format="json")
    assert no_password.status_code == 400 and "current_password" in no_password.data
    for _ in range(2):
        taken = client.patch("/api/auth/me/", {"email": "student@example.com", "current_password": PASSWORD}, format="json")
        assert taken.status_code == 400 and "email" in taken.data
    blocked = client.patch("/api/auth/me/", {"email": "fresh@example.com", "current_password": PASSWORD}, format="json")
    assert blocked.status_code == 429
    # Other profile changes still work.
    assert client.patch("/api/auth/me/", {"first_name": "Eric"}, format="json").status_code == 200
    assert AuditLog.objects.filter(action="email_in_use", target_id=str(other_student.pk)).exists()


def test_email_change_password_guesses_are_locked(other_student, client_for):
    client = client_for(other_student)
    for _ in range(4):
        response = client.patch("/api/auth/me/", {"email": "x@example.com", "current_password": "nope"}, format="json")
        assert response.status_code == 400
    assert client.patch("/api/auth/me/", {"email": "x@example.com", "current_password": "nope"}, format="json").status_code == 429
    right = client.patch("/api/auth/me/", {"email": "x@example.com", "current_password": PASSWORD}, format="json")
    assert right.status_code == 429  # locked for a while even with the right password
    assert AuditLog.objects.filter(action="reauth_failed").count() >= 5


def test_change_password_guesses_are_locked(other_student, client_for):
    client = client_for(other_student)
    for _ in range(4):
        response = client.post(
            "/api/auth/password/", {"current_password": "nope", "new_password": "Brand-new-pass-1"}, format="json"
        )
        assert response.status_code == 400 and "current_password" in response.data
    response = client.post("/api/auth/password/", {"current_password": "nope", "new_password": "Brand-new-pass-1"}, format="json")
    assert response.status_code == 429


def test_email_change_works_with_the_password_and_is_logged(other_student, client_for):
    response = client_for(other_student).patch(
        "/api/auth/me/", {"email": "New@Example.com", "current_password": PASSWORD}, format="json"
    )
    assert response.status_code == 200 and response.data["email"] == "new@example.com"
    assert AuditLog.objects.filter(action="email_changed", target_id=str(other_student.pk)).exists()
    # Saving the same address again needs no password.
    same = client_for(User.objects.get(pk=other_student.pk)).patch(
        "/api/auth/me/", {"email": "new@example.com", "first_name": "E"}, format="json"
    )
    assert same.status_code == 200


def test_roster_preview_can_test_only_a_few_emails_an_hour(teacher, student, client_for, settings):
    settings.EMAIL_IN_USE_LIMIT = 2
    classroom = Classroom.objects.create(name="S2", teacher=teacher, grade="S2")
    client = client_for(teacher)

    def preview(csv):
        return client.post(f"/api/classes/{classroom.id}/import_roster/", {"csv": csv}, format="json")

    first = preview("first_name,email\nA,student@example.com\nB,teacher@example.com\nC,free@example.com")
    assert first.status_code == 200
    assert preview("first_name,email\nD,free2@example.com").status_code == 429
    assert preview("first_name\nE").status_code == 200  # lists without emails still work


def test_parent_codes_for_deactivated_students_look_like_any_bad_code(student, client_for):
    parent = make_user("mama", role=User.Role.PARENT)
    code = client_for(student).post("/api/auth/parent-code/").data["code"]
    User.objects.filter(pk=student.pk).update(is_active=False)
    deactivated = client_for(parent).post("/api/children/", {"code": code}, format="json")
    unknown = client_for(parent).post("/api/children/", {"code": "ZZZZZZZZ"}, format="json")
    assert deactivated.status_code == unknown.status_code == 400
    assert deactivated.data == unknown.data
