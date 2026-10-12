"""The money ledger: every money event is an entry, entries never change, the chain shows tampering,
and gross, provider fee and net are worked out on the server."""

import csv
import io
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib import admin as django_admin
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory
from django.utils import timezone

from apps.core.models import AuditLog
from apps.schools import billing, flutterwave, ledger
from apps.schools.models import LedgerEntry, LedgerError, Payment, School

from .conftest import make_school, make_user

pytestmark = pytest.mark.django_db
postgres_only = pytest.mark.skipif(connection.vendor != "postgresql", reason="PostgreSQL trigger")


@pytest.fixture
def lycee(db):
    return make_school("Lycée de Kigali", "Nyarugenge")


@pytest.fixture
def lycee_admin(lycee):
    return make_user("lkadmin", role="school_admin", school=lycee)


@pytest.fixture
def staff(db):
    return make_user("staff", role="admin")


@pytest.fixture
def fw(settings, monkeypatch):
    settings.BILLING_PROVIDER = "flutterwave"
    settings.FLUTTERWAVE_SECRET_KEY = "FLWSECK_TEST-x"
    settings.FLUTTERWAVE_WEBHOOK_HASH = "webhook-secret"
    responses = {}

    def fake_request(method, path, payload=None):
        for prefix, body in responses.items():
            if path.startswith(prefix):
                return body
        raise AssertionError(f"unexpected call {method} {path}")

    monkeypatch.setattr(flutterwave, "_request", fake_request)
    return responses


def pay_online(client, payment, fw, **data):
    fw["/transactions/verify_by_reference"] = {
        "status": "success",
        "data": {"id": 500 + Payment.objects.count(), "tx_ref": payment.reference, "status": "successful", **data},
    }
    return client.post(f"/api/billing/payments/{payment.reference}/confirm/").data


def money_trail(client_for, lycee, lycee_admin, staff, fw):
    """A payment by card, a bank transfer, free months, a refund and a correction."""
    card = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    pay_online(client_for(lycee_admin), card, fw, amount="200", charged_amount="207.60", app_fee="7.60", currency="USD")
    admin = client_for(staff)
    url = f"/api/admin/schools/{lycee.id}/payments/"
    admin.post(url, {"months": 3, "amount": "600", "currency": "USD", "note": "BK", "external_reference": "BK-1"}, format="json")
    admin.post(url, {"months": 1, "amount": "0", "currency": "USD", "note": "Pilot: one free month"}, format="json")
    ledger_url = f"/api/admin/schools/{lycee.id}/ledger/"
    refund = admin.post(
        ledger_url,
        {"kind": "refund", "currency": "USD", "amount": "-600", "months": -3, "corrects": 2, "note": "Refund BK-1"},
        format="json",
    )
    correction = admin.post(
        ledger_url, {"kind": "correction", "currency": "USD", "amount": "0", "months": 1, "note": "Outage week"}, format="json"
    )
    return card, refund, correction


# --- S32 + S11: what goes in ----------------------------------------------------------------------


def test_every_money_event_is_written_with_its_money_and_dates(client_for, lycee, lycee_admin, staff, fw):
    card, refund, correction = money_trail(client_for, lycee, lycee_admin, staff, fw)
    assert refund.status_code == 201 and correction.status_code == 201
    entries = list(LedgerEntry.objects.order_by("sequence"))
    assert [e.kind for e in entries] == ["payment", "payment", "free_months", "refund", "correction"]
    assert [(e.gross_amount, e.provider_fee, e.net_amount) for e in entries] == [
        (Decimal("207.60"), Decimal("7.60"), Decimal("200.00")),  # the payer bore Flutterwave's fee
        (Decimal("600.00"), Decimal("0.00"), Decimal("600.00")),
        (Decimal("0.00"), Decimal("0.00"), Decimal("0.00")),
        (Decimal("-600.00"), Decimal("0.00"), Decimal("-600.00")),
        (Decimal("0.00"), Decimal("0.00"), Decimal("0.00")),
    ]
    assert [e.months for e in entries] == [1, 3, 1, -3, 1]
    # Each entry starts where the one before ended, and the last one is the school's date.
    for before, after in zip(entries, entries[1:], strict=False):
        assert after.paid_until_before == before.paid_until_after
    lycee.refresh_from_db()
    assert entries[-1].paid_until_after == lycee.paid_until
    assert entries[3].corrects == entries[1] and entries[3].payment == entries[1].payment
    assert entries[1].actor_name == "staff" and entries[1].reference == "BK-1"
    card.refresh_from_db()
    assert (card.gross_amount, card.provider_fee, card.net_amount) == (Decimal("207.60"), Decimal("7.60"), Decimal("200.00"))
    assert ledger.verify().ok
    assert {a.action for a in AuditLog.objects.all()} >= {
        "subscription_paid",
        "manual_payment",
        "ledger_refund",
        "ledger_correction",
    }


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"amount": "200", "app_fee": "2.80"}, ("200.00", "2.80", "197.20")),  # Iga bears the fee
        ({"amount": "200", "charged_amount": "202.80", "app_fee": "2.80"}, ("202.80", "2.80", "200.00")),
        ({"amount": "200"}, ("200.00", "0.00", "200.00")),  # no fee reported
        ({"amount": "200", "app_fee": "-5"}, ("200.00", "0.00", "200.00")),  # impossible fees are ignored
        ({"amount": "200", "app_fee": "500"}, ("200.00", "0.00", "200.00")),
        ({"amount": "200", "app_fee": "NaN"}, ("200.00", "0.00", "200.00")),
        ({"amount": "200", "charged_amount": "150", "app_fee": "1"}, ("200.00", "1.00", "199.00")),
    ],
)
def test_gross_fee_and_net_come_from_the_verified_transaction(client_for, lycee, lycee_admin, fw, data, expected):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    assert pay_online(client_for(lycee_admin), payment, fw, currency="USD", **data)["status"] == "succeeded"
    payment.refresh_from_db()
    entry = LedgerEntry.objects.get()
    expected = tuple(Decimal(v) for v in expected)
    assert (payment.gross_amount, payment.provider_fee, payment.net_amount) == expected
    assert (entry.gross_amount, entry.provider_fee, entry.net_amount) == expected


def test_platform_admins_see_the_money_and_school_admins_do_not(client_for, lycee, lycee_admin, staff, fw):
    money_trail(client_for, lycee, lycee_admin, staff, fw)
    detail = client_for(staff).get(f"/api/admin/schools/{lycee.id}/").data
    card = next(p for p in detail["payments"] if p["provider"] == "flutterwave")
    assert (card["gross_amount"], card["provider_fee"], card["net_amount"]) == ("207.60", "7.60", "200.00")
    assert [e["sequence"] for e in detail["ledger"]] == [5, 4, 3, 2, 1]
    assert client_for(staff).get(f"/api/admin/schools/{lycee.id}/ledger/").data[0]["kind"] == "correction"
    own = client_for(lycee_admin).get("/api/school/payments/").data
    assert all("provider_fee" not in p and "net_amount" not in p for p in own)
    assert client_for(lycee_admin).get(f"/api/admin/schools/{lycee.id}/ledger/").status_code == 403
    totals = client_for(staff).get("/api/admin/stats/").data["subscriptions"]["ledger"]["all_time"]
    assert totals == {"USD": {"gross": "207.60", "fees": "7.60", "net": "200.00"}}


def test_the_ledger_exports_as_csv_for_platform_admins_only(client_for, lycee, lycee_admin, staff, fw):
    School.objects.filter(pk=lycee.pk).update(name='=HYPERLINK("http://evil.example","x")')
    money_trail(client_for, lycee, lycee_admin, staff, fw)
    assert client_for(lycee_admin).get("/api/admin/ledger/export/").status_code == 403
    response = client_for(staff).get("/api/admin/ledger/export/")
    assert response.status_code == 200 and response["Content-Type"].startswith("text/csv")
    assert response["Content-Disposition"].startswith("attachment;")
    rows = list(csv.DictReader(io.StringIO(response.content.decode())))
    assert [r["sequence"] for r in rows] == ["1", "2", "3", "4", "5"]
    assert (rows[0]["gross"], rows[0]["provider_fee"], rows[0]["net"]) == ("207.60", "7.60", "200.00")
    assert rows[3]["gross"] == "-600.00" and rows[3]["corrects"] == "2"  # numbers stay numbers
    assert rows[0]["school"].startswith("'=")  # a formula is shown as text, never run
    assert rows[4]["entry_hash"] == LedgerEntry.objects.get(sequence=5).entry_hash
    only_school = client_for(staff).get("/api/admin/ledger/export/", {"school": lycee.id, "since": "2000-01-01"})
    assert only_school.status_code == 200
    assert client_for(staff).get("/api/admin/ledger/export/", {"since": "yesterday"}).status_code == 400
    assert AuditLog.objects.filter(action="export_ledger").count() == 2


# --- S32: corrections are new entries -------------------------------------------------------------


def test_corrections_never_change_the_entry_they_correct(client_for, lycee, staff):
    client = client_for(staff)
    client.post(
        f"/api/admin/schools/{lycee.id}/payments/",
        {"months": 2, "amount": "400", "currency": "USD", "note": "BK", "external_reference": "BK-77"},
        format="json",
    )
    original = LedgerEntry.objects.get()
    snapshot = {f.name: getattr(original, f.name) for f in LedgerEntry._meta.fields}
    url = f"/api/admin/schools/{lycee.id}/ledger/"
    body = {"kind": "correction", "currency": "USD", "amount": "-200", "months": -1, "corrects": 1, "note": "One month too many"}
    response = client.post(url, body, format="json", HTTP_IDEMPOTENCY_KEY="fix-0001-abcd")
    assert response.status_code == 201
    again = client.post(url, body, format="json", HTTP_IDEMPOTENCY_KEY="fix-0001-abcd")
    assert again.status_code == 200 and again.data["sequence"] == response.data["sequence"]
    original.refresh_from_db()
    assert {f.name: getattr(original, f.name) for f in LedgerEntry._meta.fields} == snapshot
    lycee.refresh_from_db()
    assert lycee.paid_until == billing.add_months(timezone.localtime(original.paid_until_after), -1)
    assert LedgerEntry.objects.count() == 2 and ledger.verify().ok


@pytest.mark.parametrize(
    "body",
    [
        {"kind": "refund", "currency": "USD", "amount": "200", "note": "x"},  # a refund is money out
        {"kind": "correction", "currency": "USD", "amount": "0", "months": 0, "note": "x"},  # changes nothing
        {"kind": "correction", "currency": "USD", "amount": "10", "note": "  "},
        {"kind": "correction", "currency": "USD", "amount": "10", "provider_fee": "20", "note": "x"},
        {"kind": "correction", "currency": "USD", "amount": "10", "months": 25, "note": "x"},
        {"kind": "correction", "currency": "USD", "amount": "0", "months": -1, "note": "x"},  # nothing to take back
        {"kind": "payment", "currency": "USD", "amount": "10", "note": "x"},  # payments come from payments
        {"kind": "correction", "currency": "USD", "amount": "10", "corrects": 99, "note": "x"},
    ],
)
def test_impossible_corrections_are_refused(client_for, lycee, staff, body):
    assert client_for(staff).post(f"/api/admin/schools/{lycee.id}/ledger/", body, format="json").status_code == 400
    assert not LedgerEntry.objects.exists()


def test_a_correction_cannot_point_at_another_schools_entry(client_for, lycee, staff):
    apade = make_school("APADE", "Kicukiro")
    billing.record_manual_payment(apade, staff, 1, Decimal("200"), "USD", "BK")
    body = {"kind": "correction", "currency": "USD", "amount": "-200", "corrects": 1, "note": "x"}
    assert client_for(staff).post(f"/api/admin/schools/{lycee.id}/ledger/", body, format="json").status_code == 400


# --- S32: entries can't be changed -----------------------------------------------------------------


def test_entries_cannot_be_changed_or_deleted_through_the_model(lycee, staff):
    billing.record_manual_payment(lycee, staff, 1, Decimal("200"), "USD", "BK")
    entry = LedgerEntry.objects.get()
    entry.gross_amount = Decimal("1")
    with pytest.raises(LedgerError):
        entry.save()
    with pytest.raises(LedgerError):
        entry.delete()
    with pytest.raises(LedgerError):
        LedgerEntry.objects.filter(pk=entry.pk).update(gross_amount=Decimal("1"))
    with pytest.raises(LedgerError):
        LedgerEntry.objects.all().delete()
    with pytest.raises(LedgerError):
        LedgerEntry.objects.create(**{f.attname: getattr(entry, f.attname) for f in LedgerEntry._meta.fields if f.name != "id"})
    with pytest.raises(LedgerError):
        LedgerEntry.objects.bulk_create([LedgerEntry(sequence=9)])
    entry.refresh_from_db()
    assert entry.gross_amount == Decimal("200.00")
    # A paid payment and its school can't be deleted from under the ledger either.
    with pytest.raises(Exception):  # noqa: B017 - ProtectedError
        Payment.objects.get().delete()


def test_the_django_admin_shows_money_records_read_only(staff):
    request = RequestFactory().get("/")
    request.user = make_user("root", role="admin", is_staff=True, is_superuser=True)
    for model in (LedgerEntry, Payment):
        model_admin = django_admin.site._registry[model]
        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
    assert "paid_until" in django_admin.site._registry[School].readonly_fields


@postgres_only
def test_postgres_refuses_updates_and_deletes_even_in_raw_sql(lycee, staff):
    billing.record_manual_payment(lycee, staff, 1, Decimal("200"), "USD", "BK")
    for sql in (
        "UPDATE schools_ledgerentry SET gross_amount = 1",
        "DELETE FROM schools_ledgerentry",
    ):
        with pytest.raises(DatabaseError, match="append-only"), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(sql)
    assert LedgerEntry.objects.get().gross_amount == Decimal("200.00")


# --- S32: tampering is detected --------------------------------------------------------------------


def _tamper(sql, params=()):
    """Change the table behind the application's back, as someone with database access could."""
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")  # run the deferred foreign-key checks first
            cursor.execute("ALTER TABLE schools_ledgerentry DISABLE TRIGGER schools_ledgerentry_append_only")
        cursor.execute(sql, params)
        if connection.vendor == "postgresql":
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute("ALTER TABLE schools_ledgerentry ENABLE TRIGGER schools_ledgerentry_append_only")


def _three_payments(lycee, staff):
    for i in range(3):
        billing.record_manual_payment(lycee, staff, 1, Decimal("200"), "USD", f"BK {i}", external_reference=f"BK-{i}")


def test_an_edited_amount_is_detected(lycee, staff):
    _three_payments(lycee, staff)
    report = ledger.verify()
    assert report.ok and report.entries == 3
    _tamper("UPDATE schools_ledgerentry SET gross_amount = 2, net_amount = 2 WHERE sequence = 2")
    problems = ledger.verify().problems
    assert any("#2: its contents changed" in p for p in problems)
    assert any("amount differs" in p for p in problems)
    with pytest.raises(CommandError):
        call_command("verify_ledger")


def test_a_removed_entry_is_detected(lycee, staff):
    _three_payments(lycee, staff)
    _tamper("DELETE FROM schools_ledgerentry WHERE sequence = 2")
    problems = ledger.verify().problems
    assert any("#3: expected entry #2" in p for p in problems)
    assert any("#3: does not follow" in p for p in problems)
    assert any("paid but has no ledger entry" in p for p in problems)


def test_a_wiped_ledger_is_detected(lycee, staff):
    _three_payments(lycee, staff)
    _tamper("DELETE FROM schools_ledgerentry")
    assert len([p for p in ledger.verify().problems if "no ledger entry" in p]) == 3


def test_a_rebuilt_chain_is_caught_by_the_recorded_head_or_the_key(lycee, staff, settings):
    _three_payments(lycee, staff)
    report = ledger.verify()
    head = f"{report.head_sequence}:{report.head_hash}"
    out = io.StringIO()
    call_command("verify_ledger", "--expect-head", head, stdout=out)
    assert head in out.getvalue()

    # Someone changes a note and recomputes every hash from there on (they know the algorithm).
    def rebuild(alg, key=b"", start=1, edit=2):
        previous = LedgerEntry.objects.get(sequence=start - 1).entry_hash if start > 1 else ledger.GENESIS
        for entry in LedgerEntry.objects.filter(sequence__gte=start).order_by("sequence"):
            fields = ledger.hash_fields(entry)
            if entry.sequence == edit:
                fields["note"] = "changed"
                _tamper("UPDATE schools_ledgerentry SET note = 'changed' WHERE id = %s", [entry.pk])
            digest = ledger.compute_hash(fields, previous, alg, key)
            _tamper(
                "UPDATE schools_ledgerentry SET prev_hash = %s, entry_hash = %s, hash_alg = %s WHERE id = %s",
                [previous, digest, alg, entry.pk],
            )
            previous = digest

    rebuild("sha256")
    assert ledger.verify().ok  # the chain alone can't tell...
    assert not ledger.verify(expect_head=head).ok  # ...but the head kept elsewhere can
    with pytest.raises(CommandError):
        call_command("verify_ledger", "--expect-head", head)

    # With LEDGER_HMAC_KEY set, new entries are HMAC-signed and a rebuild without the key fails.
    settings.LEDGER_HMAC_KEY = "the-real-key"
    for i in range(2):
        billing.record_manual_payment(lycee, staff, 1, Decimal("200"), "USD", "BK keyed", external_reference=f"BK-K{i}")
    report = ledger.verify()
    assert report.ok and not report.warnings
    assert list(LedgerEntry.objects.values_list("hash_alg", flat=True)) == ["sha256"] * 3 + ["hmac-sha256"] * 2
    rebuild("hmac-sha256", b"a-guess", start=5, edit=5)
    assert any("#5: its contents changed" in p for p in ledger.verify().problems)
    rebuild("sha256", start=5, edit=5)  # going back to plain hashes after a keyed entry
    assert any("#5: unexpected hash algorithm" in p for p in ledger.verify().problems)
    rebuild("sha256", start=4, edit=4)  # rebuilding everything since the key without it
    report = ledger.verify()
    assert report.warnings == ["the newest entry is not signed with LEDGER_HMAC_KEY"]
    err = io.StringIO()
    call_command("verify_ledger", stdout=io.StringIO(), stderr=err)
    assert "not signed" in err.getvalue()


def test_payments_made_before_the_ledger_get_their_entries(lycee, lycee_admin):
    """Migration 0004 writes an opening entry for every payment already paid."""
    from importlib import import_module

    now = timezone.now()
    for i, provider in enumerate(("manual", "flutterwave")):
        Payment.objects.create(
            reference=f"old-{i}",
            school=lycee,
            provider=provider,
            months=1,
            amount=Decimal("200"),
            currency="USD",
            status="succeeded",
            paid_at=now - timedelta(days=10 - i),
            period_start=now,
            period_end=now + timedelta(days=30),
            provider_data={"amount": 200, "charged_amount": "203", "app_fee": "3"} if provider == "flutterwave" else {},
        )
    assert not ledger.verify().ok  # paid payments without entries
    historical = MigrationExecutor(connection).loader.project_state(("schools", "0004_ledger_append_only")).apps
    import_module("apps.schools.migrations.0004_ledger_append_only").backfill(historical, None)
    entries = list(LedgerEntry.objects.order_by("sequence"))
    assert [e.payment.reference for e in entries] == ["old-0", "old-1"]
    assert (entries[1].gross_amount, entries[1].provider_fee, entries[1].net_amount) == (
        Decimal("203.00"),
        Decimal("3.00"),
        Decimal("200.00"),
    )
    assert ledger.verify().ok
