"""Ending sessions when credentials change (S23), and refresh-token reuse detection."""

import base64
import json
from datetime import timedelta

import pyotp
import pytest
from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.accounts.models import User
from apps.classroom.models import Classroom, Enrollment
from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"
NEW_PASSWORD = "An0ther-pass-456"


def device(identifier="student", password=PASSWORD):
    """A logged-in browser: refresh cookie stored, access token sent as a Bearer header."""
    client = APIClient()
    response = client.post("/api/auth/login/", {"identifier": identifier, "password": password}, format="json")
    assert response.status_code == 200, response.data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


def can_use_access_token(client):
    return client.get("/api/auth/me/").status_code == 200


def can_refresh(client):
    return client.post("/api/auth/refresh/").status_code == 200


def age_blacklist(minutes=5):
    for entry in BlacklistedToken.objects.all():
        entry.blacklisted_at -= timedelta(minutes=minutes)
        entry.save()


def test_password_change_ends_other_sessions_at_once_and_keeps_this_one(student):
    phone, laptop = device(), device()
    response = laptop.post("/api/auth/password/", {"current_password": PASSWORD, "new_password": NEW_PASSWORD}, format="json")
    assert response.status_code == 200
    # The phone's access token stops working now, not when it expires in 15 minutes.
    assert not can_use_access_token(phone)
    assert not can_refresh(phone)
    # This device gets a new access token in the answer and a new refresh cookie.
    laptop.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    assert can_use_access_token(laptop)
    assert can_refresh(laptop)
    entry = AuditLog.objects.get(action="change_password")
    assert entry.details["other_sessions_ended"] is True


def test_a_device_ended_by_a_password_change_is_not_mistaken_for_a_thief(student):
    phone, laptop = device(), device()
    laptop.post("/api/auth/password/", {"current_password": PASSWORD, "new_password": NEW_PASSWORD}, format="json")
    age_blacklist()  # the phone comes back online much later with its old cookie
    assert not can_refresh(phone)
    assert can_refresh(laptop)  # the laptop's new session survives
    assert not AuditLog.objects.filter(action="refresh_token_reuse").exists()


@pytest.mark.parametrize("action", ["enable", "disable"])
def test_2fa_changes_end_other_sessions(student, action):
    secret = pyotp.random_base32()
    student.totp_secret = secret
    student.totp_enabled = action == "disable"
    student.save()
    other = device() if action == "enable" else None
    if action == "disable":
        other = APIClient()
        response = other.post(
            "/api/auth/login/",
            {"identifier": "student", "password": PASSWORD, "otp": pyotp.TOTP(secret).now()},
            format="json",
        )
        other.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        User.objects.filter(pk=student.pk).update(totp_last_step=None)  # as if the next 30 s window came
    current = APIClient()
    current.force_authenticate(User.objects.get(pk=student.pk))
    response = current.post(f"/api/auth/2fa/{action}/", {"otp": pyotp.TOTP(secret).now()}, format="json")
    assert response.status_code == 200, response.data
    assert response.data["access"]
    assert not can_use_access_token(other)
    assert not can_refresh(other)
    assert AuditLog.objects.filter(action=f"{action}_2fa").exists()


def test_teacher_password_reset_ends_the_students_sessions(student, teacher, client_for):
    classroom = Classroom.objects.create(name="S2 Maths", teacher=teacher, grade="S2")
    Enrollment.objects.create(classroom=classroom, student=student)
    phone = device()
    response = client_for(teacher).post(f"/api/classes/{classroom.id}/reset_password/", {"student": student.id}, format="json")
    assert response.status_code == 200
    assert not can_use_access_token(phone)
    assert not can_refresh(phone)
    entry = AuditLog.objects.get(action="reset_student_password")
    assert entry.target_id == str(student.pk) and entry.actor == teacher


def test_a_password_set_anywhere_ends_sessions(student):
    """The Django admin, manage.py changepassword or a shell all go through User.save()."""
    phone = device()
    user = User.objects.get(pk=student.pk)
    user.set_password(NEW_PASSWORD)
    user.save()
    assert not can_use_access_token(phone)
    assert not can_refresh(phone)


def test_the_automatic_rehash_at_login_keeps_other_sessions(student):
    phone = device()
    User.objects.filter(pk=student.pk).update(password=make_password(PASSWORD, hasher="pbkdf2_sha256"))
    device()  # this login upgrades the hash to Argon2id
    assert User.objects.get(pk=student.pk).password.startswith("argon2")
    assert can_use_access_token(phone)
    assert can_refresh(phone)


def test_logout_everywhere(student):
    phone, laptop = device(), device()
    response = laptop.post("/api/auth/logout-all/")
    assert response.status_code == 204
    for client in (phone, laptop):
        assert not can_use_access_token(client)
        assert not can_refresh(client)
    assert AuditLog.objects.filter(action="logout_everywhere").exists()


def test_deactivated_accounts_are_logged_out_everywhere(student, admin_user, client_for):
    phone = device()
    response = client_for(admin_user).patch(f"/api/admin/users/{student.id}/", {"is_active": False}, format="json")
    assert response.status_code == 200
    User.objects.filter(pk=student.pk).update(is_active=True)  # even if reactivated later
    assert not can_use_access_token(phone)
    assert not can_refresh(phone)


def test_reused_refresh_token_still_ends_every_session(student):
    client = device()
    stolen = client.cookies["iga_refresh"].value
    assert can_refresh(client)
    age_blacklist()
    thief = APIClient()
    thief.cookies["iga_refresh"] = stolen
    assert not can_refresh(thief)
    assert not can_refresh(client)
    assert not can_use_access_token(client)  # the access token ends too
    assert AuditLog.objects.filter(action="refresh_token_reuse", target_id=str(student.pk)).exists()


def test_a_forged_refresh_cookie_cannot_log_someone_else_out(student, other_student):
    """Reuse detection must not trust an unsigned token naming another user."""
    victim = device("other")
    attacker = device("student")
    own_old = attacker.cookies["iga_refresh"].value
    assert can_refresh(attacker)  # the attacker's own old token is now "used"
    age_blacklist()
    header, payload, signature = own_old.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["user_id"] = str(other_student.pk)
    edited = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    forged = APIClient()
    forged.cookies["iga_refresh"] = f"{header}.{edited}.{signature}"
    assert forged.post("/api/auth/refresh/").status_code == 401
    assert can_refresh(victim)
    assert can_use_access_token(victim)
    assert not AuditLog.objects.filter(action="refresh_token_reuse", target_id=str(other_student.pk)).exists()
