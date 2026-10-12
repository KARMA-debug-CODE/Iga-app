"""Password reset by email (S16) and other one-time secrets: single use, short lifetime, invalidated
by a reset, a password change, an email change or a newer link; temporary passwords and parent codes."""

import hashlib
import re
from datetime import timedelta

import pyotp
import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts import password_reset
from apps.accounts.models import ParentInvite, PasswordResetToken, User
from apps.classroom.models import Classroom, Enrollment
from apps.core.models import AuditLog

from .conftest import RELAXED_RATES, make_user

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"
NEW_PASSWORD = "Fresh-pass-2026"


@pytest.fixture(autouse=True)
def _send_now(monkeypatch):
    """The real code sends after answering, in a thread; here it runs inline so the test can see it."""
    monkeypatch.setattr(password_reset, "deliver", lambda work, *args: work(*args))


def ask(identifier, client=None):
    return (client or APIClient()).post("/api/auth/password-reset/", {"identifier": identifier}, format="json")


def link_token():
    assert mail.outbox, "no email was sent"
    match = re.search(r"/reset-password#(\S+)", mail.outbox[-1].body)
    return match.group(1)


def confirm(token, password=NEW_PASSWORD):
    return APIClient().post("/api/auth/password-reset/confirm/", {"token": token, "new_password": password}, format="json")


def can_log_in(password, identifier="student"):
    response = APIClient().post("/api/auth/login/", {"identifier": identifier, "password": password}, format="json")
    return response.status_code == 200


def test_reset_by_username_or_email_sends_a_single_use_link(student):
    for identifier in ("student", "STUDENT@example.com"):
        mail.outbox.clear()
        response = ask(identifier)
        assert response.status_code == 200
        assert mail.outbox[0].to == ["student@example.com"]
    token = link_token()
    # Only a hash of the secret is stored, and the link keeps the secret out of server logs (#).
    stored = PasswordResetToken.objects.get(user=student)
    assert stored.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in str(PasswordResetToken.objects.values_list())
    assert "#" in mail.outbox[-1].body and "?token" not in mail.outbox[-1].body

    assert confirm(token).status_code == 200
    assert can_log_in(NEW_PASSWORD) and not can_log_in(PASSWORD)
    again = confirm(token, "Another-pass-2027")
    assert again.status_code == 400 and again.data["code"] == "invalid_link"
    assert can_log_in(NEW_PASSWORD)
    assert AuditLog.objects.filter(action="password_reset", target_id=str(student.pk)).exists()


def test_the_answer_is_the_same_whether_or_not_the_account_exists(student):
    nobody_email = make_user("noemail")
    User.objects.filter(pk=nobody_email.pk).update(email=None)
    inactive = make_user("gone")
    User.objects.filter(pk=inactive.pk).update(is_active=False)
    answers = {}
    for identifier in ("student", "ghost", "ghost@example.com", "noemail", "gone"):
        response = ask(identifier)
        answers[identifier] = (response.status_code, response.data)
    assert len(set(map(str, answers.values()))) == 1
    assert [m.to for m in mail.outbox] == [["student@example.com"]]


def test_the_answer_does_the_same_work_whether_or_not_the_account_exists(student, monkeypatch, django_assert_num_queries):
    """The lookup, the link and the email all happen after the answer, so its timing can't tell."""
    deferred = []
    monkeypatch.setattr(password_reset, "deliver", lambda work, *args: deferred.append(args))
    with django_assert_num_queries(1):  # the audit entry, the same for everyone
        ask("student")
    with django_assert_num_queries(1):
        ask("nobody-here")
    assert len(deferred) == 2 and not mail.outbox


def test_link_expires_after_an_hour(student, monkeypatch):
    ask("student")
    token = link_token()
    stored = PasswordResetToken.objects.get(user=student)
    assert timedelta(minutes=59) < stored.expires_at - stored.created_at <= timedelta(minutes=60)
    later = timezone.now() + timedelta(minutes=61)
    monkeypatch.setattr(timezone, "now", lambda: later)
    assert confirm(token).status_code == 400
    assert can_log_in(PASSWORD)


def test_a_newer_link_replaces_the_older_one(student):
    ask("student")
    first = link_token()
    ask("student")
    second = link_token()
    assert confirm(first).status_code == 400
    assert confirm(second).status_code == 200


def test_changing_the_password_invalidates_the_link(student, client_for):
    ask("student")
    token = link_token()
    client = APIClient()
    login = client.post("/api/auth/login/", {"identifier": "student", "password": PASSWORD}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    changed = client.post("/api/auth/password/", {"current_password": PASSWORD, "new_password": "Changed-pass-77"}, format="json")
    assert changed.status_code == 200
    assert confirm(token).status_code == 400


def test_a_teacher_reset_invalidates_the_link(student, teacher, client_for):
    classroom = Classroom.objects.create(name="S2", teacher=teacher, grade="S2")
    Enrollment.objects.create(classroom=classroom, student=student)
    ask("student")
    token = link_token()
    client_for(teacher).post(f"/api/classes/{classroom.id}/reset_password/", {"student": student.id}, format="json")
    assert confirm(token).status_code == 400


def test_changing_the_email_invalidates_the_link(student, client_for):
    ask("student")
    token = link_token()
    response = client_for(student).patch(
        "/api/auth/me/", {"email": "new-address@example.com", "current_password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    assert confirm(token).status_code == 400


def test_a_weak_new_password_is_refused_and_the_link_still_works(student):
    ask("student")
    token = link_token()
    weak = confirm(token, "password123")
    assert weak.status_code == 400 and "new_password" in weak.data
    assert confirm(token).status_code == 200


def test_a_reset_ends_every_session(student):
    phone = APIClient()
    login = phone.post("/api/auth/login/", {"identifier": "student", "password": PASSWORD}, format="json")
    phone.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    ask("student")
    assert confirm(link_token()).status_code == 200
    assert phone.get("/api/auth/me/").status_code == 401
    assert phone.post("/api/auth/refresh/").status_code == 401


def test_a_reset_does_not_bypass_two_factor(student):
    student.totp_secret = pyotp.random_base32()
    student.totp_enabled = True
    student.save()
    ask("student")
    response = confirm(link_token())
    assert response.status_code == 200 and "access" not in response.data  # no automatic login
    login = APIClient().post("/api/auth/login/", {"identifier": "student", "password": NEW_PASSWORD}, format="json")
    assert login.status_code == 401 and login.data["otp_required"]


def test_reset_email_is_in_the_users_language(student):
    User.objects.filter(pk=student.pk).update(preferred_language="fr")
    ask("student")
    assert "nouveau mot de passe" in mail.outbox[0].subject
    assert "60 minutes" in mail.outbox[0].body


def test_reset_requests_are_limited_per_account_the_same_for_made_up_ones(student, monkeypatch):
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RELAXED_RATES, "password_reset": "2/hour"})
    for identifier in ("student", "made-up-name"):
        codes = [ask(identifier).status_code for _ in range(3)]
        assert codes == [200, 200, 429]
    assert len(mail.outbox) == 2


def test_garbage_tokens_are_refused(student):
    for token in ("", "x" * 129, "not-a-real-token"):
        assert confirm(token).status_code == 400


# --- Temporary passwords from a teacher ---------------------------------------------------


@pytest.fixture
def classroom(teacher):
    return Classroom.objects.create(name="S2 Maths", teacher=teacher, grade="S2")


def test_temporary_passwords_expire(teacher, classroom, client_for, settings, monkeypatch):
    settings.TEMPORARY_PASSWORD_DAYS = 14
    created = (
        client_for(teacher)
        .post(f"/api/classes/{classroom.id}/import_roster/", {"csv": "first_name\nKalisa", "confirm": True}, format="json")
        .data["created"][0]
    )
    user = User.objects.get(username=created["username"])
    assert timedelta(days=13) < user.temporary_password_expires_at - timezone.now() <= timedelta(days=14)

    later = timezone.now() + timedelta(days=15)
    monkeypatch.setattr(timezone, "now", lambda: later)
    response = APIClient().post(
        "/api/auth/login/", {"identifier": created["username"], "password": created["temporary_password"]}, format="json"
    )
    assert response.status_code == 403 and response.data["code"] == "temporary_password_expired"

    # The teacher hands out a new one, which works.
    Enrollment.objects.get_or_create(classroom=classroom, student=user)
    reset = client_for(teacher).post(f"/api/classes/{classroom.id}/reset_password/", {"student": user.id}, format="json")
    login = APIClient().post(
        "/api/auth/login/", {"identifier": created["username"], "password": reset.data["temporary_password"]}, format="json"
    )
    assert login.status_code == 200


def test_a_temporary_password_holder_cannot_change_the_email(teacher, classroom, client_for):
    created = (
        client_for(teacher)
        .post(f"/api/classes/{classroom.id}/import_roster/", {"csv": "first_name\nKalisa", "confirm": True}, format="json")
        .data["created"][0]
    )
    client = APIClient()
    login = client.post(
        "/api/auth/login/", {"identifier": created["username"], "password": created["temporary_password"]}, format="json"
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    attempt = client.patch(
        "/api/auth/me/",
        {"email": "teacher-inbox@example.com", "current_password": created["temporary_password"]},
        format="json",
    )
    assert attempt.status_code == 403
    assert client.patch("/api/auth/me/", {"preferred_language": "fr"}, format="json").status_code == 200
    assert User.objects.get(username=created["username"]).email is None


# --- Parent codes ----------------------------------------------------------------------


def test_parent_codes_are_single_use_expire_and_are_replaced(student, client_for):
    parent = make_user("mama", role=User.Role.PARENT)
    other_parent = make_user("papa", role=User.Role.PARENT)
    kid = client_for(student)
    first = kid.post("/api/auth/parent-code/").data["code"]
    second = kid.post("/api/auth/parent-code/").data["code"]
    assert client_for(parent).post("/api/children/", {"code": first}, format="json").status_code == 400  # replaced
    assert client_for(parent).post("/api/children/", {"code": second}, format="json").status_code == 201
    assert client_for(other_parent).post("/api/children/", {"code": second}, format="json").status_code == 400  # used

    third = kid.post("/api/auth/parent-code/").data["code"]
    ParentInvite.objects.filter(code=third).update(expires_at=timezone.now() - timedelta(seconds=1))
    assert client_for(other_parent).post("/api/children/", {"code": third}, format="json").status_code == 400
