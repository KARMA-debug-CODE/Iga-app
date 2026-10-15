"""Two requests at the same moment can't both redeem the same thing (S31) and money changes run
under row locks (S36). These start real threads on separate database connections, so they run on
PostgreSQL, as CI does (SQLite allows only one writer at a time, so it can't show a race)."""

import threading
import time
from datetime import timedelta
from decimal import Decimal

import pyotp
import pytest
from django.db import connection, connections
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import ParentInvite, ParentLink, User, parent_code_digest
from apps.accounts.security import verify_totp
from apps.classroom.models import Classroom, Enrollment
from apps.core.models import AuditLog
from apps.curriculum.models import LessonProgress
from apps.gamification.models import XPEvent
from apps.schools import billing, flutterwave, ledger
from apps.schools.models import LedgerEntry, Payment
from apps.schools.providers import Verification

from .conftest import make_school, make_user

pytestmark = [
    pytest.mark.skipif(connection.vendor != "postgresql", reason="needs PostgreSQL row locks"),
    pytest.mark.django_db(transaction=True),
]
RACERS = 6


def race(*jobs):
    """Run the jobs at the same moment, each in its own thread and database connection.
    Returns each job's result, or the exception it raised."""
    barrier = threading.Barrier(len(jobs))
    results = [None] * len(jobs)

    def run(index, job):
        try:
            connection.ensure_connection()
            barrier.wait(timeout=30)
            results[index] = job()
        except Exception as exc:  # collected and checked by the test
            results[index] = exc
        finally:
            connections.close_all()

    threads = [threading.Thread(target=run, args=(i, job)) for i, job in enumerate(jobs)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    assert not any(thread.is_alive() for thread in threads), "a racer hung"
    return results


@pytest.fixture
def slow_money(monkeypatch):
    """Widen the window between reading and writing a subscription, so an unlocked read would race."""
    real = billing.add_months

    def slow(moment, months):
        time.sleep(0.05)
        return real(moment, months)

    monkeypatch.setattr(billing, "add_months", slow)


@pytest.fixture
def school(db):
    return make_school("Lycée de Kigali", "Nyarugenge")


@pytest.fixture
def school_admin(school):
    return make_user("lkadmin", role="school_admin", school=school)


@pytest.fixture
def staff(db):
    return make_user("staff", role="admin")


def months_between(start, end):
    return (end.year - start.year) * 12 + end.month - start.month


def test_racing_confirmations_apply_a_payment_once(school, school_admin, slow_money):
    payment = billing.start_payment(school, school_admin, 1, "USD", "flutterwave")
    data = {"id": 900, "tx_ref": payment.reference, "status": "successful", "amount": "200", "currency": "USD"}

    def confirm():
        return billing.settle(Payment.objects.get(pk=payment.pk), Verification("succeeded", "900", data)).status

    assert race(*[confirm] * RACERS) == ["succeeded"] * RACERS
    school.refresh_from_db()
    payment.refresh_from_db()
    assert school.paid_until == payment.period_end
    assert months_between(payment.period_start, school.paid_until) == 1
    assert LedgerEntry.objects.count() == 1
    assert AuditLog.objects.filter(action="subscription_paid").count() == 1


def test_racing_payments_for_one_school_all_count(school, school_admin, slow_money):
    """Different payments for the same school at once: none is lost (the school row is locked)."""
    payments = [billing.start_payment(school, school_admin, months, "USD", "dev") for months in (1, 3, 6, 12)]
    started = timezone.now()
    results = race(*[(lambda p=p: billing.apply_payment(p)) for p in payments])
    assert results == [True] * 4
    school.refresh_from_db()
    entries = list(LedgerEntry.objects.order_by("sequence"))
    assert sorted(e.months for e in entries) == [1, 3, 6, 12]
    for before, after in zip(entries, entries[1:], strict=False):
        assert after.paid_until_before == before.paid_until_after  # each one started where the last ended
    assert entries[-1].paid_until_after == school.paid_until
    assert months_between(timezone.localtime(started), timezone.localtime(school.paid_until)) == 22
    assert ledger.verify().ok


def test_racing_webhook_and_redirect_apply_a_payment_once(school, school_admin, settings, monkeypatch):
    settings.BILLING_PROVIDER = "flutterwave"
    settings.FLUTTERWAVE_SECRET_KEY = "FLWSECK_TEST-x"
    settings.FLUTTERWAVE_WEBHOOK_HASH = "webhook-secret"
    payment = billing.start_payment(school, school_admin, 1, "USD", "flutterwave")
    answer = {
        "status": "success",
        "data": {"id": 901, "tx_ref": payment.reference, "status": "successful", "amount": "200", "currency": "USD"},
    }
    monkeypatch.setattr(flutterwave, "_request", lambda method, path, payload=None: answer)
    body = {"event": "charge.completed", "data": {"id": 901, "tx_ref": payment.reference}}

    def webhook():
        return APIClient().post("/api/billing/webhooks/flutterwave/", body, format="json", HTTP_VERIF_HASH="webhook-secret")

    def redirect():
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=school_admin.pk))
        return client.post(f"/api/billing/payments/{payment.reference}/confirm/", {"transaction_id": "901"}, format="json")

    responses = race(webhook, redirect, webhook, redirect)
    assert all(r.status_code == 200 for r in responses), responses
    assert LedgerEntry.objects.count() == 1
    school.refresh_from_db()
    assert months_between(timezone.localtime(Payment.objects.get().period_start), timezone.localtime(school.paid_until)) == 1


def test_identical_webhooks_at_the_same_moment_ask_flutterwave_once(school, school_admin, settings, monkeypatch):
    settings.BILLING_PROVIDER = "flutterwave"
    settings.FLUTTERWAVE_SECRET_KEY = "FLWSECK_TEST-x"
    settings.FLUTTERWAVE_WEBHOOK_HASH = "webhook-secret"
    payment = billing.start_payment(school, school_admin, 1, "USD", "flutterwave")
    calls = []

    def fake_request(method, path, payload=None):
        calls.append(path)
        time.sleep(0.1)
        return {"status": "success", "data": {"id": 902, "tx_ref": payment.reference, "status": "pending"}}

    monkeypatch.setattr(flutterwave, "_request", fake_request)
    body = {"event": "charge.completed", "data": {"id": 902, "tx_ref": payment.reference}}

    def deliver():
        return APIClient().post("/api/billing/webhooks/flutterwave/", body, format="json", HTTP_VERIF_HASH="webhook-secret").data

    results = race(*[deliver] * RACERS)
    assert sorted(r.get("received", False) for r in results) == [False] * (RACERS - 1) + [True]
    assert len(calls) == 1


def test_racing_records_of_one_bank_transfer_record_it_once(school, staff, slow_money):
    def record(i):
        return billing.record_manual_payment_once(
            school,
            staff,
            1,
            Decimal("200"),
            "USD",
            "Bank of Kigali",
            external_reference="BK-4471",
            idempotency_key=f"key-{i:08d}",
        )

    results = race(*[(lambda i=i: record(i)) for i in range(RACERS)])
    created = [r for r in results if isinstance(r, tuple)]
    refused = [r for r in results if isinstance(r, ValidationError)]
    assert len(created) == 1 and len(refused) == RACERS - 1, results
    assert Payment.objects.count() == 1 and LedgerEntry.objects.count() == 1
    school.refresh_from_db()
    assert months_between(timezone.localtime(Payment.objects.get().period_start), timezone.localtime(school.paid_until)) == 1


def test_racing_resends_of_one_request_record_it_once(school, staff):
    def record():
        payment, created = billing.record_manual_payment_once(
            school, staff, 1, Decimal("0"), "USD", "Pilot month", idempotency_key="same-key-123"
        )
        return payment.pk, created

    results = race(*[record] * RACERS)
    assert len({pk for pk, _created in results}) == 1
    assert sorted(created for _pk, created in results) == [False] * (RACERS - 1) + [True]
    assert Payment.objects.count() == 1 and LedgerEntry.objects.count() == 1


def test_racing_ledger_appends_keep_one_unbroken_chain(staff):
    schools = [make_school(f"School {i}", "Gasabo") for i in range(8)]

    def correct(school):
        return billing.record_correction(school, staff, "correction", "USD", Decimal("10"), "Goodwill credit")[0].sequence

    sequences = race(*[(lambda s=s: correct(s)) for s in schools])
    assert sorted(sequences) == list(range(1, 9))
    assert ledger.verify().ok


def test_racing_parents_cannot_both_use_one_link_code(db):
    student = make_user("child")
    parents = [make_user(f"parent{i}", role=User.Role.PARENT, school=None) for i in range(RACERS)]
    ParentInvite.objects.create(
        student=student, code_hash=parent_code_digest("ABCD2345"), expires_at=timezone.now() + timedelta(days=1)
    )

    def redeem(parent):
        client = APIClient()
        client.force_authenticate(parent)
        return client.post("/api/children/", {"code": "ABCD2345"}, format="json").status_code

    codes = race(*[(lambda p=p: redeem(p)) for p in parents])
    assert sorted(codes) == [201] + [400] * (RACERS - 1)
    assert ParentLink.objects.count() == 1
    assert ParentInvite.objects.get().used_by_id == ParentLink.objects.get().parent_id


def test_racing_resets_cannot_both_use_one_password_reset_link(db):
    from apps.accounts import password_reset

    user = make_user("forgetful")
    token = password_reset.create_link(user).split("#", 1)[1]
    passwords = [f"Racing-pass-{i}-Kigali" for i in range(RACERS)]

    def confirm(password):
        body = {"token": token, "new_password": password}
        return APIClient().post("/api/auth/password-reset/confirm/", body, format="json").status_code

    codes = race(*[(lambda p=p: confirm(p)) for p in passwords])
    assert sorted(codes) == [200] + [400] * (RACERS - 1)
    user.refresh_from_db()
    assert sum(user.check_password(p) for p in passwords) == 1


def test_racing_logins_cannot_both_spend_one_totp_code(db):
    user = make_user("secure", totp_secret=pyotp.random_base32(), totp_enabled=True)
    code = pyotp.TOTP(user.totp_secret).now()
    results = race(*[(lambda: verify_totp(User.objects.get(pk=user.pk), code))] * RACERS)
    assert sorted(results) == [False] * (RACERS - 1) + [True]


def test_racing_lesson_completions_award_xp_once(lesson):
    student = make_user("racer")

    def complete():
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=student.pk))
        return client.post(f"/api/lessons/{lesson.slug}/complete/").status_code

    assert race(*[complete] * RACERS) == [200] * RACERS
    assert LessonProgress.objects.filter(user=student).count() == 1
    assert XPEvent.objects.filter(user=student, reference=f"lesson:{lesson.pk}").count() == 1
    student.refresh_from_db()
    assert student.xp == 10


def test_racing_quiz_submits_award_xp_once(quiz_factory):
    student = make_user("racer")
    quiz = quiz_factory()
    client = APIClient()
    client.force_authenticate(student)
    attempt = client.post(f"/api/quizzes/{quiz.id}/start/").data
    first = attempt["questions"][0]
    client.post(
        f"/api/attempts/{attempt['id']}/answer/",
        {"question": first["id"], "choice_ids": [first["choices"][0]["id"]]},
        format="json",
    )

    def submit():
        racer = APIClient()
        racer.force_authenticate(User.objects.get(pk=student.pk))
        return racer.post(f"/api/attempts/{attempt['id']}/submit/").status_code

    assert race(*[submit] * RACERS) == [200] * RACERS
    assert XPEvent.objects.filter(user=student, reference=f"quiz:{quiz.pk}").count() == 1


def test_racing_class_joins_enrol_once(teacher):
    classroom = Classroom.objects.create(name="S2 A", teacher=teacher, grade="S2")
    student = make_user("racer")

    def join():
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=student.pk))
        return client.post("/api/classes/join/", {"code": classroom.join_code}, format="json").status_code

    assert race(*[join] * RACERS) == [200] * RACERS
    assert Enrollment.objects.filter(classroom=classroom, student=student).count() == 1
