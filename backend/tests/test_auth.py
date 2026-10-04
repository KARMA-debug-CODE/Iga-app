import time

import pyotp
import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def register(client, **overrides):
    payload = {
        "username": "newkid",
        "email": "newkid@example.com",
        "password": "Str0ng-pass-123",
        "first_name": "New",
        "last_name": "Kid",
        "grade": "S1",
    }
    payload.update(overrides)
    return client.post("/api/auth/register/", payload, format="json")


def test_student_registration_returns_access_token_and_httponly_refresh_cookie(client_for):
    response = register(client_for())
    assert response.status_code == 201
    assert response.data["access"]
    assert response.data["user"]["role"] == "student"
    cookie = response.cookies["iga_refresh"]
    assert cookie["httponly"]
    assert cookie["path"] == "/api/auth/"


def test_student_must_choose_grade(client_for):
    response = register(client_for(), grade="")
    assert response.status_code == 400
    assert "grade" in response.data


def test_weak_password_rejected(client_for):
    response = register(client_for(), password="12345678")
    assert response.status_code == 400


def test_cannot_self_register_as_admin(client_for):
    response = register(client_for(), role="admin")
    assert response.status_code == 400


def test_self_registered_teacher_needs_approval(client_for):
    response = register(client_for(), username="mwalimu", email="t@example.com", role="teacher", grade="")
    assert response.status_code == 201
    teacher = User.objects.get(username="mwalimu")
    assert teacher.teacher_approved is False
    response = client_for(teacher).post("/api/classes/", {"name": "S1 Maths", "grade": "S1"}, format="json")
    assert response.status_code == 403


def test_login_with_email_or_username(client_for, student):
    client = client_for()
    for identifier in ("student", "STUDENT@example.com"):
        response = client.post("/api/auth/login/", {"identifier": identifier, "password": "Str0ng-pass-123"}, format="json")
        assert response.status_code == 200, identifier


def test_wrong_password(client_for, student):
    response = client_for().post("/api/auth/login/", {"identifier": "student", "password": "nope"}, format="json")
    assert response.status_code == 401


def test_refresh_cookie_issues_new_access_token_and_logout_clears_it(client_for, student):
    client = client_for()
    client.post("/api/auth/login/", {"identifier": "student", "password": "Str0ng-pass-123"}, format="json")
    response = client.post("/api/auth/refresh/")
    assert response.status_code == 200
    me = client_for()
    me.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    assert me.get("/api/auth/me/").data["username"] == "student"

    client.post("/api/auth/logout/")
    assert client.post("/api/auth/refresh/").status_code == 401


def test_refresh_without_cookie(client_for):
    assert client_for().post("/api/auth/refresh/").status_code == 401


def test_profile_update_cannot_change_role(client_for, student):
    client = client_for(student)
    response = client.patch("/api/auth/me/", {"preferred_language": "fr", "role": "admin", "xp": 9999}, format="json")
    assert response.status_code == 200
    student.refresh_from_db()
    assert student.preferred_language == "fr"
    assert student.role == "student"
    assert student.xp == 0


def test_two_factor_flow(client_for, student):
    client = client_for(student)
    secret = client.post("/api/auth/2fa/setup/").data["secret"]
    assert client.post("/api/auth/2fa/enable/", {"otp": "000000"}, format="json").status_code == 400
    assert client.post("/api/auth/2fa/enable/", {"otp": pyotp.TOTP(secret).now()}, format="json").status_code == 200

    anon = client_for()
    response = anon.post("/api/auth/login/", {"identifier": "student", "password": "Str0ng-pass-123"}, format="json")
    assert response.status_code == 401 and response.data["otp_required"]
    # Each code works once, so later steps use the next 30-second codes (within the drift window).
    totp = pyotp.TOTP(secret)
    response = anon.post(
        "/api/auth/login/",
        {"identifier": "student", "password": "Str0ng-pass-123", "otp": totp.at(time.time() + 30)},
        format="json",
    )
    assert response.status_code == 200

    # Replaying the same code is refused.
    replay = anon.post(
        "/api/auth/login/",
        {"identifier": "student", "password": "Str0ng-pass-123", "otp": totp.at(time.time() + 30)},
        format="json",
    )
    assert replay.status_code == 401

    assert client.post("/api/auth/2fa/disable/", {"otp": totp.at(time.time() + 30)}, format="json").status_code == 400
    User.objects.filter(pk=student.pk).update(totp_last_step=None)  # as if the next 30 s window had arrived
    assert client.post("/api/auth/2fa/disable/", {"otp": totp.now()}, format="json").status_code == 200
    student.refresh_from_db()
    assert not student.totp_enabled and not student.totp_secret


def test_change_password(client_for, student):
    client = client_for(student)
    response = client.post(
        "/api/auth/password/", {"current_password": "wrong", "new_password": "An0ther-pass-456"}, format="json"
    )
    assert response.status_code == 400
    response = client.post(
        "/api/auth/password/", {"current_password": "Str0ng-pass-123", "new_password": "An0ther-pass-456"}, format="json"
    )
    assert response.status_code == 200
    student.refresh_from_db()
    assert student.check_password("An0ther-pass-456")


def test_login_is_throttled_per_account_not_per_ip(client_for, student, other_student, monkeypatch):
    from rest_framework.throttling import SimpleRateThrottle

    from .conftest import RELAXED_RATES

    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RELAXED_RATES, "login": "3/min"})
    client = client_for()
    for _ in range(3):
        client.post("/api/auth/login/", {"identifier": "student", "password": "wrong"}, format="json")
    blocked = client.post("/api/auth/login/", {"identifier": "student", "password": "Str0ng-pass-123"}, format="json")
    assert blocked.status_code == 429
    # A classmate behind the same school IP can still log in.
    ok = client.post("/api/auth/login/", {"identifier": "other", "password": "Str0ng-pass-123"}, format="json")
    assert ok.status_code == 200
