"""Sign-in rate limits and progressive lockout, per account and per IP (S7/S43), and their logging (S19)."""

import json
import logging
import time

import pyotp
import pytest
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.core.models import AuditLog

from .conftest import RELAXED_RATES, make_user

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"


def attempt(identifier, password, ip="10.0.0.1", **extra):
    return APIClient().post(
        "/api/auth/login/", {"identifier": identifier, "password": password, **extra}, format="json", REMOTE_ADDR=ip
    )


@pytest.fixture
def clock(monkeypatch):
    """Moves time forward for the lockout and the cache alike."""
    now = [time.time()]
    monkeypatch.setattr(time, "time", lambda: now[0])

    def advance(seconds):
        now[0] += seconds

    return advance


def security_lines(caplog):
    return [json.loads(r.getMessage()) for r in caplog.records if r.name == "iga.security"]


def test_five_failures_lock_the_account_even_for_the_right_password(student, caplog):
    caplog.set_level(logging.INFO, logger="iga.security")
    for _ in range(4):
        assert attempt("student", "wrong").status_code == 401
    locked = attempt("student", "wrong")
    assert locked.status_code == 429
    assert int(locked["Retry-After"]) > 0
    assert "Too many failed attempts" in locked.data["detail"]
    # The right password doesn't get in while the lock lasts, and says nothing about the password.
    blocked = attempt("student", PASSWORD)
    assert blocked.status_code == 429 and "access" not in blocked.data

    actions = list(AuditLog.objects.values_list("action", flat=True))
    assert actions.count("login_failed") == 5
    assert "account_locked" in actions and "login_locked" in actions
    events = [line["event"] for line in security_lines(caplog)]
    assert events.count("login_failed") == 5 and "account_locked" in events


def test_lockout_answers_are_the_same_for_made_up_accounts(student):
    def sequence(identifier):
        answers = [attempt(identifier, "wrong") for _ in range(6)]
        return [(a.status_code, a.data["detail"]) for a in answers]

    assert sequence("student") == sequence("nobody-at-all")
    assert sequence("student@example.com") == sequence("nobody@example.com")


def test_lock_expires_and_each_new_lock_doubles(student, clock, settings):
    settings.LOGIN_LOCKOUT_BASE_SECONDS = 60
    for _ in range(5):
        attempt("student", "wrong")
    assert attempt("student", PASSWORD).status_code == 429
    clock(61)
    assert attempt("student", PASSWORD).status_code == 200

    for _ in range(5):
        attempt("student", "wrong")
    second = attempt("student", PASSWORD)
    assert second.status_code == 429 and 60 < int(second["Retry-After"]) <= 121
    clock(70)
    assert attempt("student", PASSWORD).status_code == 429  # 2 minutes this time
    clock(60)
    assert attempt("student", PASSWORD).status_code == 200


def test_lock_is_capped(student, clock, settings):
    settings.LOGIN_LOCKOUT_MAX_SECONDS = 300
    for _ in range(6):  # six locks in a day: 60, 120, 240, then the 300 s cap
        for _ in range(5):
            attempt("student", "wrong")
        wait = int(attempt("student", PASSWORD)["Retry-After"])
        clock(wait + 1)
    assert wait <= 301


def test_a_successful_login_resets_the_failures_in_a_row(student):
    for _ in range(4):
        attempt("student", "wrong")
    assert attempt("student", PASSWORD).status_code == 200
    for _ in range(4):
        assert attempt("student", "wrong").status_code == 401
    assert attempt("student", PASSWORD).status_code == 200


def test_attacker_elsewhere_does_not_lock_the_student_out_after_five_tries(student):
    for _ in range(5):
        attempt("student", "wrong", ip="203.0.113.9")
    assert attempt("student", PASSWORD, ip="203.0.113.9").status_code == 429
    assert attempt("student", PASSWORD, ip="41.186.1.9").status_code == 200  # the student at school


def test_guesses_spread_over_many_addresses_still_lock_the_account(student, settings):
    settings.LOGIN_LOCKOUT_ACCOUNT_THRESHOLD = 12
    for n in range(3):
        for _ in range(4):
            attempt("student", "wrong", ip=f"198.51.100.{n}")
    assert attempt("student", PASSWORD, ip="198.51.100.200").status_code == 429


def test_one_address_failing_on_many_accounts_is_locked(student, other_student, settings):
    settings.LOGIN_LOCKOUT_IP_THRESHOLD = 6
    for n in range(6):
        attempt(f"guess{n}", "wrong", ip="192.0.2.50")
    assert attempt("student", PASSWORD, ip="192.0.2.50").status_code == 429
    assert attempt("student", PASSWORD, ip="192.0.2.51").status_code == 200


def test_username_spellings_share_one_lock(student):
    for spelling in ("student", "STUDENT", " Student ", "stUdent", "student"):
        attempt(spelling, "wrong")
    assert attempt("student", PASSWORD).status_code == 429


def test_lookalike_spellings_never_reach_the_account(student):
    # PostgreSQL's case-insensitive match treats a dotless i like i; sign-in must not.
    make_user("aline")
    assert attempt("alıne", PASSWORD).status_code == 401
    assert attempt("aline", PASSWORD).status_code == 200


def test_wrong_2fa_codes_count_towards_the_lock(student):
    student.totp_secret = pyotp.random_base32()
    student.totp_enabled = True
    student.save()
    for _ in range(4):
        response = attempt("student", PASSWORD, otp="000000")
        assert response.status_code == 401 and response.data["otp_required"]
    assert attempt("student", PASSWORD, otp="000000").status_code == 429
    right = attempt("student", PASSWORD, otp=pyotp.TOTP(student.totp_secret).now())
    assert right.status_code == 429
    assert AuditLog.objects.filter(action="login_failed", details__reason="otp").count() == 5


def test_wrong_codes_lock_2fa_changes(student, client_for):
    student.totp_secret = pyotp.random_base32()
    student.totp_enabled = True
    student.save()
    client = client_for(student)
    for _ in range(4):
        assert client.post("/api/auth/2fa/disable/", {"otp": "000000"}, format="json").status_code == 400
    assert client.post("/api/auth/2fa/disable/", {"otp": "000000"}, format="json").status_code == 429
    code = pyotp.TOTP(student.totp_secret).now()
    assert client.post("/api/auth/2fa/disable/", {"otp": code}, format="json").status_code == 429
    student.refresh_from_db()
    assert student.totp_enabled
    assert AuditLog.objects.filter(action="2fa_failed", target_id=str(student.pk)).count() >= 5


def test_throttled_requests_are_logged_once_in_the_audit_log_and_every_time_in_the_log(student, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="iga.security")
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RELAXED_RATES, "login": "2/min"})
    codes = [attempt("student", PASSWORD).status_code for _ in range(5)]
    assert codes == [200, 200, 429, 429, 429]
    assert AuditLog.objects.filter(action="throttled").count() == 1
    assert [line["event"] for line in security_lines(caplog)].count("throttled") == 3


def test_registration_is_limited_per_address(monkeypatch):
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RELAXED_RATES, "register": "2/hour"})
    client = APIClient()

    def register(n):
        payload = {"username": f"kid{n}", "password": PASSWORD, "first_name": "K", "grade": "S1"}
        return client.post("/api/auth/register/", payload, format="json", REMOTE_ADDR="10.9.9.9").status_code

    assert [register(n) for n in range(3)] == [201, 201, 429]
    other = client.post(
        "/api/auth/register/",
        {"username": "kid9", "password": PASSWORD, "first_name": "K", "grade": "S1"},
        format="json",
        REMOTE_ADDR="10.9.9.10",
    )
    assert other.status_code == 201


def test_refresh_is_limited_per_account_but_forged_tokens_use_nobodys_allowance(student, monkeypatch):
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RELAXED_RATES, "refresh_user": "2/min"})
    client = APIClient()
    client.post("/api/auth/login/", {"identifier": "student", "password": PASSWORD}, format="json")
    # Someone sends made-up tokens naming the student: they don't count against the student.
    forged = APIClient()
    forged.cookies["iga_refresh"] = client.cookies["iga_refresh"].value[:-4] + "AAAA"
    for _ in range(3):
        assert forged.post("/api/auth/refresh/").status_code == 401
    assert client.post("/api/auth/refresh/").status_code == 200
    assert client.post("/api/auth/refresh/").status_code == 200
    assert client.post("/api/auth/refresh/").status_code == 429


def test_password_and_codes_never_reach_the_security_log(student, caplog):
    caplog.set_level(logging.INFO, logger="iga.security")
    attempt("student", "My-Secret-Guess-1")
    attempt("Str0ng-pass-123", "oops")  # a password typed into the username box
    attempt("student", PASSWORD)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "My-Secret-Guess-1" not in text and PASSWORD not in text
    stored = json.dumps([e.details for e in AuditLog.objects.all()])
    assert "My-Secret-Guess-1" not in stored and PASSWORD not in stored and "oops" not in stored
    login = AuditLog.objects.get(action="login")
    assert login.target_id == str(student.pk) and login.ip_address == "10.0.0.1"


def test_refused_requests_are_logged(student, client_for):
    client = client_for(student)
    for _ in range(3):
        assert client.get("/api/admin/stats/").status_code == 403
    entries = AuditLog.objects.filter(action="permission_denied")
    assert entries.count() == 1 and entries.first().details["username"] == "student"


def test_admin_can_list_security_events(admin_user, student, client_for):
    attempt("student", "wrong")
    attempt("student", PASSWORD)
    response = client_for(admin_user).get("/api/admin/audit/", {"security": "1"})
    assert response.status_code == 200
    actions = {row["action"] for row in response.data}
    assert {"login", "login_failed"} <= actions


def test_admin_site_logins_are_logged_and_share_the_lockout(db, settings):
    from django.test import RequestFactory

    from apps.accounts.models import User
    from apps.core.admin_login import OTPAdminAuthenticationForm

    settings.ADMIN_REQUIRE_2FA = False

    def form(password, ip="10.0.0.7"):
        request = RequestFactory().post("/django-admin/login/", REMOTE_ADDR=ip)
        return OTPAdminAuthenticationForm(request, data={"username": "boss", "password": password})

    make_user("boss", role=User.Role.ADMIN, is_staff=True)
    assert not form("wrong").is_valid()
    assert form(PASSWORD).is_valid()
    actions = list(AuditLog.objects.values_list("action", flat=True))
    assert "admin_login_failed" in actions and "admin_login" in actions

    for _ in range(5):
        assert not form("wrong").is_valid()
    locked = form(PASSWORD)
    assert not locked.is_valid() and "Too many attempts" in str(locked.errors)
    # The app's sign-in sees the same lock for that account and address.
    assert attempt("boss", PASSWORD, ip="10.0.0.7").status_code == 429
