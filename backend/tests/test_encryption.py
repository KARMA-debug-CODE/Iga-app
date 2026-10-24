"""Secrets and personal data encrypted (or hashed) in the database (S33)."""

import base64
import json
import os
import subprocess
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pyotp
import pytest
from cryptography.fernet import Fernet
from django.conf import settings as django_settings
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from apps.accounts.models import ParentInvite, User, parent_code_digest
from apps.accounts.security import verify_totp
from apps.core import encryption
from apps.schools.models import Payment, School

from .conftest import make_user

BACKEND = Path(__file__).resolve().parent.parent


def raw(table, column, pk):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} FROM {table} WHERE id = %s", [pk])
        return cursor.fetchone()[0]


def raw_payment_data(pk):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT provider_data FROM schools_payment WHERE id = %s", [Payment._meta.pk.get_db_prep_value(pk, connection)]
        )
        value = cursor.fetchone()[0]
    return value if isinstance(value, str) else json.dumps(value)  # PostgreSQL hands jsonb back decoded


@pytest.mark.django_db
def test_totp_secrets_are_encrypted_in_the_database(student, client_for):
    secret = client_for(student).post("/api/auth/2fa/setup/").data["secret"]
    stored = raw("accounts_user", "totp_secret", student.pk)
    assert stored.startswith("fernet:") and secret not in stored
    user = User.objects.get(pk=student.pk)
    assert user.totp_secret == secret
    assert verify_totp(user, pyotp.TOTP(secret).now())


@pytest.mark.django_db
def test_an_empty_secret_stays_empty(student):
    assert raw("accounts_user", "totp_secret", student.pk) == ""
    assert User.objects.filter(pk=student.pk, totp_secret="").exists()


@pytest.mark.django_db
def test_school_phone_numbers_are_encrypted(client_for):
    school = School.objects.create(name="GS Remera", district="Gasabo", phone="+250 788 123 456")
    stored = raw("schools_school", "phone", school.pk)
    assert stored.startswith("fernet:") and "788" not in stored
    assert School.objects.get(pk=school.pk).phone == "+250 788 123 456"


# What Flutterwave's verify endpoint answers about a transaction (trimmed): it names the payer.
FLUTTERWAVE_ANSWER = {
    "id": 4975213,
    "status": "successful",
    "amount": 200,
    "currency": "USD",
    "customer": {"name": "Jean Mugisha", "phone_number": "0788123456", "email": "head@gsremera.rw"},
    "card": {"first_6digits": "553188", "last_4digits": "2950", "expiry": "09/32"},
}


@pytest.mark.django_db
def test_payment_provider_answers_are_encrypted():
    school = School.objects.create(name="GS Remera", district="Gasabo")
    payment = Payment.objects.create(
        reference="IGA-T1", school=school, provider="flutterwave", months=1, amount=Decimal(200), currency="USD"
    )
    payment.provider_data = FLUTTERWAVE_ANSWER
    payment.save()
    stored = raw_payment_data(payment.pk)
    assert stored.startswith("fernet:")
    for personal in ("0788123456", "head@gsremera.rw", "Mugisha", "2950"):
        assert personal not in stored
    assert Payment.objects.get(pk=payment.pk).provider_data == FLUTTERWAVE_ANSWER
    assert Payment.objects.filter(pk=payment.pk).values_list("provider_data", flat=True).get() == FLUTTERWAVE_ANSWER
    # A new payment's empty answer is a dict, as before; exports (dumpdata) still hold the data itself.
    assert (
        Payment.objects.create(
            reference="IGA-T2", school=school, provider="manual", months=1, amount=Decimal(0), currency="USD"
        ).provider_data
        == {}
    )
    exported = json.loads(serializers.serialize("json", [Payment.objects.get(pk=payment.pk)]))
    assert exported[0]["fields"]["provider_data"] == FLUTTERWAVE_ANSWER


@pytest.mark.django_db
def test_the_database_holds_no_working_refresh_token(student):
    """Attack: copy a refresh token out of the database (a backup, a dump, the Django admin) and use it."""
    victim = APIClient()
    login = victim.post("/api/auth/login/", {"identifier": "student", "password": "Str0ng-pass-123"}, format="json")
    assert login.status_code == 200
    stored = OutstandingToken.objects.get(user=student).token
    cookie = victim.cookies[django_settings.REFRESH_COOKIE_NAME].value
    # Header and claims only (who, until when, the token's id): no signature.
    assert stored.endswith(".") and stored.count(".") == 2 and stored.split(".")[0] == cookie.split(".")[0]

    thief = APIClient()
    thief.cookies[django_settings.REFRESH_COOKIE_NAME] = stored
    assert thief.post("/api/auth/refresh/").status_code == 401
    # The real cookie still works, rotates, and its replacement is stored unsigned too.
    refreshed = victim.post("/api/auth/refresh/")
    assert refreshed.status_code == 200
    assert OutstandingToken.objects.filter(user=student).count() == 2
    assert all(token.endswith(".") for token in OutstandingToken.objects.values_list("token", flat=True))
    # Logging out everywhere still finds every session (by the token's id).
    victim.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}")
    assert victim.post("/api/auth/logout-all/").status_code == 204
    assert not OutstandingToken.objects.filter(user=student, blacklistedtoken__isnull=True).exists()


@pytest.mark.django_db
def test_parent_codes_are_kept_only_as_keyed_hashes(student, client_for):
    code = client_for(student).post("/api/auth/parent-code/").data["code"]
    invite = ParentInvite.objects.get(student=student)
    assert invite.code_hash == parent_code_digest(code) and code not in invite.code_hash
    parent = make_user("mama", role=User.Role.PARENT)
    linked = client_for(parent).post("/api/children/", {"code": code.lower()}, format="json")
    assert linked.status_code == 201


@pytest.mark.django_db
def test_keys_rotate(student, settings):
    old_key, new_key = settings.FIELD_ENCRYPTION_KEYS[0], Fernet.generate_key().decode()
    student.totp_secret = "JBSWY3DPEHPK3PXP"
    student.save()
    before = raw("accounts_user", "totp_secret", student.pk)
    school = School.objects.create(name="GS Remera", district="Gasabo", phone="0788123456")
    payment = Payment.objects.create(
        reference="IGA-R1", school=school, provider="dev", months=1, amount=Decimal(1), currency="USD", provider_data={"a": 1}
    )

    settings.FIELD_ENCRYPTION_KEYS = [new_key, old_key]  # the new key first, the old one still readable
    assert User.objects.get(pk=student.pk).totp_secret == "JBSWY3DPEHPK3PXP"
    call_command("rotate_field_encryption", stdout=open(os.devnull, "w"))
    after = raw("accounts_user", "totp_secret", student.pk)
    assert after != before

    settings.FIELD_ENCRYPTION_KEYS = [new_key]  # the old key removed
    assert User.objects.get(pk=student.pk).totp_secret == "JBSWY3DPEHPK3PXP"
    assert School.objects.get(pk=school.pk).phone == "0788123456"
    assert Payment.objects.get(pk=payment.pk).provider_data == {"a": 1}


@pytest.mark.django_db
def test_a_wrong_key_fails_loudly(student, settings):
    student.totp_secret = "JBSWY3DPEHPK3PXP"
    student.save()
    settings.FIELD_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    with pytest.raises(ImproperlyConfigured):
        User.objects.get(pk=student.pk)


def test_values_written_before_encryption_are_still_read():
    assert encryption.decrypt("JBSWY3DPEHPK3PXP") == "JBSWY3DPEHPK3PXP"


def _settings_with(**env):
    base = {"PATH": os.environ.get("PATH", ""), "DJANGO_SECRET_KEY": "x" * 50}
    code = "from config import settings; print(len(settings.FIELD_ENCRYPTION_KEYS))"
    return subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env={**base, **env}, capture_output=True, text=True)


def test_production_refuses_to_start_without_a_real_key():
    missing = _settings_with()
    assert missing.returncode != 0 and "FIELD_ENCRYPTION_KEYS" in missing.stderr
    invalid = _settings_with(FIELD_ENCRYPTION_KEYS="change-me")
    assert invalid.returncode != 0 and "Fernet keys" in invalid.stderr
    # Valid Fernet keys that are not secret: a phrase, a run of one character.
    for weak in (b"test-only-field-encryption-key!!", bytes(32), b"\x01\x02" * 16):
        refused = _settings_with(FIELD_ENCRYPTION_KEYS=base64.urlsafe_b64encode(weak).decode())
        assert refused.returncode != 0 and "not random" in refused.stderr
    good = _settings_with(FIELD_ENCRYPTION_KEYS=f"{Fernet.generate_key().decode()},{Fernet.generate_key().decode()}")
    assert good.returncode == 0 and good.stdout.strip() == "2"
    # Local development (DEBUG on) works without one.
    assert _settings_with(DJANGO_DEBUG="true").returncode == 0


@pytest.mark.django_db(transaction=True)
def test_the_migrations_encrypt_and_hash_existing_rows():
    executor = MigrationExecutor(connection)
    before = [("accounts", "0012_password_reset_and_temporary_password_expiry"), ("schools", "0002_payment_checked_at")]
    # The newest migration of each app, so later ones (the money ledger's) are back in place after the test.
    latest = [node for node in executor.loader.graph.leaf_nodes() if node[0] in ("accounts", "schools")]
    executor.migrate(before)
    signed = "eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJsZWdhY3kifQ.c2lnbmF0dXJl"
    try:
        old = executor.loader.project_state([*before, *executor.loader.graph.leaf_nodes("token_blacklist")]).apps
        OldUser, OldInvite, OldSchool, OldPayment, OldToken = (
            old.get_model("accounts", "User"),
            old.get_model("accounts", "ParentInvite"),
            old.get_model("schools", "School"),
            old.get_model("schools", "Payment"),
            old.get_model("token_blacklist", "OutstandingToken"),
        )
        user = OldUser.objects.create(username="legacy", role="student", totp_secret="JBSWY3DPEHPK3PXP", totp_enabled=True)
        OldInvite.objects.create(student=user, code="ABCD2345", expires_at=timezone.now() + timedelta(days=1))
        school = OldSchool.objects.create(name="Old School", district="Gasabo", phone="0788000111")
        payment = OldPayment.objects.create(
            reference="IGA-OLD",
            school=school,
            provider="flutterwave",
            months=1,
            amount=200,
            currency="USD",
            provider_data=FLUTTERWAVE_ANSWER,
        )
        OldToken.objects.create(user=user, jti="legacy", token=signed, expires_at=timezone.now() + timedelta(days=1))
        OldToken.objects.create(user=user, jti="empty", token="", expires_at=timezone.now() + timedelta(days=1))
        assert raw("accounts_user", "totp_secret", user.pk) == "JBSWY3DPEHPK3PXP"
        assert "0788123456" in raw_payment_data(payment.pk)
    finally:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(latest)

    assert raw("accounts_user", "totp_secret", user.pk).startswith("fernet:")
    assert User.objects.get(pk=user.pk).totp_secret == "JBSWY3DPEHPK3PXP"
    assert raw("schools_school", "phone", school.pk).startswith("fernet:")
    assert School.objects.get(pk=school.pk).phone == "0788000111"
    assert raw_payment_data(payment.pk).startswith("fernet:")
    assert Payment.objects.get(pk=payment.pk).provider_data == FLUTTERWAVE_ANSWER
    assert ParentInvite.objects.get(student_id=user.pk).code_hash == parent_code_digest("ABCD2345")
    assert OutstandingToken.objects.get(jti="legacy").token == "eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJsZWdhY3kifQ."
    assert OutstandingToken.objects.get(jti="empty").token == ""

    # And back: the plain values return (unused parent codes and token signatures can't, so they go).
    executor = MigrationExecutor(connection)
    executor.migrate(before)
    try:
        assert raw("accounts_user", "totp_secret", user.pk) == "JBSWY3DPEHPK3PXP"
        assert raw("schools_school", "phone", school.pk) == "0788000111"
        assert json.loads(raw_payment_data(payment.pk)) == FLUTTERWAVE_ANSWER
    finally:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(latest)
