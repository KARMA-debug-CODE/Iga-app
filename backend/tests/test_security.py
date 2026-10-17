"""Session revocation, refresh-token reuse, one-time codes, admin login and client IPs."""

import time
from datetime import timedelta

import pyotp
import pytest
from django.test import RequestFactory, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.accounts.models import User
from apps.accounts.security import verify_totp
from apps.core.admin_login import OTPAdminAuthenticationForm
from apps.core.audit import client_ip

from .conftest import make_user

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"


def login(identifier="student", password=PASSWORD, **extra):
    client = APIClient()
    response = client.post("/api/auth/login/", {"identifier": identifier, "password": password, **extra}, format="json")
    return client, response


def refresh(client):
    return client.post("/api/auth/refresh/")


def test_refresh_token_rotates_and_works_once(student):
    client, _ = login()
    stolen = client.cookies["iga_refresh"].value
    assert refresh(client).status_code == 200
    replay = APIClient()
    replay.cookies["iga_refresh"] = stolen
    assert refresh(replay).status_code == 401


def test_reusing_an_old_refresh_token_ends_every_session(student):
    client, _ = login()
    stolen = client.cookies["iga_refresh"].value
    assert refresh(client).status_code == 200
    # Well after the two-tabs grace window, the old token comes back: assume it was stolen.
    BlacklistedToken.objects.update(blacklisted_at=BlacklistedToken.objects.first().blacklisted_at - timedelta(minutes=5))
    thief = APIClient()
    thief.cookies["iga_refresh"] = stolen
    assert refresh(thief).status_code == 401
    # The legitimate session was revoked too.
    assert refresh(client).status_code == 401


def test_simultaneous_tabs_do_not_trigger_reuse_revocation(student):
    tab1, _ = login()
    shared = tab1.cookies["iga_refresh"].value
    tab2 = APIClient()
    tab2.cookies["iga_refresh"] = shared
    assert refresh(tab1).status_code == 200
    late = refresh(tab2)
    assert late.status_code == 401
    assert "iga_refresh" not in late.cookies  # doesn't wipe the cookie tab 1 just received
    assert refresh(tab1).status_code == 200


def test_logout_blacklists_the_refresh_token(student):
    client, _ = login()
    token = client.cookies["iga_refresh"].value
    assert client.post("/api/auth/logout/").status_code == 204
    again = APIClient()
    again.cookies["iga_refresh"] = token
    assert refresh(again).status_code == 401


def test_password_change_logs_out_other_devices(student):
    phone, _ = login()
    laptop, response = login()
    laptop.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    changed = laptop.post(
        "/api/auth/password/", {"current_password": PASSWORD, "new_password": "An0ther-pass-456"}, format="json"
    )
    assert changed.status_code == 200
    assert refresh(phone).status_code == 401
    assert refresh(laptop).status_code == 200  # this device got a fresh cookie


def test_totp_code_is_single_use(student):
    student.totp_secret = pyotp.random_base32()
    student.totp_enabled = True
    student.save()
    code = pyotp.TOTP(student.totp_secret).now()
    assert verify_totp(student, code)
    assert not verify_totp(User.objects.get(pk=student.pk), code)
    # An older code from the drift window is refused too once a newer one was used.
    older = pyotp.TOTP(student.totp_secret).at(time.time() - 30)
    assert not verify_totp(User.objects.get(pk=student.pk), older)


def test_usernames_cannot_contain_at_or_collide_by_case(client_for, student):
    anon = client_for()
    base = {"password": PASSWORD, "first_name": "A", "last_name": "B", "grade": "S1", "accept_terms": True}
    response = anon.post("/api/auth/register/", {**base, "username": "x@y.rw", "email": "x@y.rw"}, format="json")
    assert response.status_code == 400 and "username" in response.data
    response = anon.post("/api/auth/register/", {**base, "username": "STUDENT", "email": "new@example.com"}, format="json")
    assert response.status_code == 400 and "username" in response.data


def test_email_is_unique_ignoring_case(client_for, student, other_student):
    client = client_for(other_student)
    response = client.patch("/api/auth/me/", {"email": "STUDENT@example.com"}, format="json")
    assert response.status_code == 400


def test_login_by_email_is_case_insensitive(student):
    _, response = login("Student@Example.com")
    assert response.status_code == 200


def _admin_form(data):
    request = RequestFactory().post("/django-admin/login/")
    return OTPAdminAuthenticationForm(request, data=data)


@override_settings(ADMIN_REQUIRE_2FA=True)
def test_admin_login_requires_two_factor(db):
    staff = make_user("boss", role=User.Role.ADMIN, is_staff=True)
    assert not _admin_form({"username": "boss", "password": PASSWORD}).is_valid()

    staff.totp_secret = pyotp.random_base32()
    staff.totp_enabled = True
    staff.save()
    assert not _admin_form({"username": "boss", "password": PASSWORD, "otp": "000000"}).is_valid()
    code = pyotp.TOTP(staff.totp_secret).now()
    assert _admin_form({"username": "boss", "password": PASSWORD, "otp": code}).is_valid()
    assert not _admin_form({"username": "boss", "password": PASSWORD, "otp": code}).is_valid()  # replay


@override_settings(ADMIN_REQUIRE_2FA=False, ADMIN_LOGIN_ATTEMPTS_PER_MINUTE=3)
def test_admin_login_attempts_are_limited(db):
    make_user("boss", role=User.Role.ADMIN, is_staff=True)
    for _ in range(3):
        assert not _admin_form({"username": "boss", "password": "wrong"}).is_valid()
    form = _admin_form({"username": "boss", "password": PASSWORD})
    assert not form.is_valid()
    assert "Too many attempts" in str(form.errors)


@pytest.mark.parametrize(
    ("hops", "forwarded", "remote", "expected"),
    [
        (0, "1.2.3.4", "10.0.0.2", "10.0.0.2"),  # no proxy: ignore the header entirely
        (1, "6.6.6.6, 41.186.1.9", "10.0.0.2", "41.186.1.9"),  # nginx appended the real address
        (1, "not-an-ip", "10.0.0.2", "10.0.0.2"),
        (2, "41.186.1.9", "10.0.0.2", "10.0.0.2"),  # fewer entries than proxies: don't guess
    ],
)
def test_client_ip_trusts_only_our_proxies(settings, hops, forwarded, remote, expected):
    settings.TRUSTED_PROXY_COUNT = hops
    request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR=forwarded, REMOTE_ADDR=remote)
    assert client_ip(request) == expected
