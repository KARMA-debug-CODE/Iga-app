"""Attacks on payments: forged and replayed webhooks, untrusted redirects, tampered prices, and the
same money credited twice. Each test first does what an attacker would, then checks it fails."""

import base64
import hashlib
import hmac
import json
import logging
from decimal import Decimal
from unittest import mock

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.models import AuditLog
from apps.schools import billing, flutterwave, webhooks
from apps.schools.models import LedgerEntry, Payment, WebhookEvent

from .conftest import make_school, make_user

pytestmark = pytest.mark.django_db

HOOK = "/api/billing/webhooks/flutterwave/"
SECRET = "webhook-secret"


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
    settings.FLUTTERWAVE_WEBHOOK_HASH = SECRET
    calls = []
    responses = {"/transactions?": {"status": "success", "data": []}}

    def fake_request(method, path, payload=None):
        calls.append((method, path, payload))
        for prefix, body in responses.items():
            if path.startswith(prefix):
                return body(path, payload) if callable(body) else body
        raise AssertionError(f"unexpected call {method} {path}")

    monkeypatch.setattr(flutterwave, "_request", fake_request)
    return {"calls": calls, "responses": responses}


def verified(payment, status="successful", transaction_id=1, amount="200.00", currency="USD", **extra):
    data = {"id": transaction_id, "tx_ref": payment.reference, "status": status, "amount": amount, "currency": currency}
    data.update(extra)
    return {"status": "success", "data": data}


def verify_calls(fw):
    return [path for _method, path, _payload in fw["calls"] if "verify" in path]


def audits(action):
    return list(AuditLog.objects.filter(action=action))


# --- S5: webhook signatures -----------------------------------------------------------------


def test_unsigned_or_forged_webhooks_are_refused_logged_and_audited(client_for, lycee, lycee_admin, fw, caplog):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    body = {"event": "charge.completed", "data": {"id": 5, "tx_ref": payment.reference, "status": "successful"}}
    anon = client_for()
    with caplog.at_level(logging.WARNING, logger="apps.schools.webhooks"):
        assert anon.post(HOOK, body, format="json").status_code == 401  # no signature
        assert anon.post(HOOK, body, format="json", HTTP_VERIF_HASH="webhook-secreT").status_code == 401
        assert anon.post(HOOK, body, format="json", HTTP_FLUTTERWAVE_SIGNATURE="bm9wZQ==").status_code == 401
    assert fw["calls"] == []  # nothing was asked of Flutterwave, let alone applied
    payment.refresh_from_db()
    assert payment.status == "pending"
    assert len([r for r in caplog.records if "Refused a flutterwave webhook" in r.getMessage()]) == 3
    rejected = audits("webhook_rejected")
    assert len(rejected) == 3 and {a.details["reason"] for a in rejected} == {"bad_signature"}
    assert WebhookEvent.objects.filter(outcome="bad_signature", signature_valid=False).count() == 3


def test_a_signed_but_unreadable_webhook_is_refused_and_audited(client_for, fw):
    response = client_for().post(HOOK, "{not json", content_type="application/json", HTTP_VERIF_HASH=SECRET)
    assert response.status_code == 400
    assert [a.details["reason"] for a in audits("webhook_rejected")] == ["unreadable"]


def test_without_a_configured_secret_every_webhook_is_refused(client_for, lycee, lycee_admin, fw, settings):
    settings.FLUTTERWAVE_WEBHOOK_HASH = ""
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    body = {"data": {"tx_ref": payment.reference}}
    assert client_for().post(HOOK, body, format="json", HTTP_VERIF_HASH="").status_code == 401
    raw = json.dumps(body).encode()
    empty_key_signature = base64.b64encode(hmac.new(b"", raw, hashlib.sha256).digest()).decode()
    response = client_for().post(HOOK, raw, content_type="application/json", HTTP_FLUTTERWAVE_SIGNATURE=empty_key_signature)
    assert response.status_code == 401


def test_hmac_signatures_cover_the_exact_body(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/verify_by_reference"] = {"status": "success", "data": {"status": "pending"}}
    raw = json.dumps({"event": "charge.completed", "data": {"tx_ref": payment.reference}}).encode()
    good = base64.b64encode(hmac.new(SECRET.encode(), raw, hashlib.sha256).digest()).decode()
    other_key = base64.b64encode(hmac.new(b"guess", raw, hashlib.sha256).digest()).decode()
    tampered = raw.replace(b"charge.completed", b"charge.completeD")
    anon = client_for()
    assert anon.post(HOOK, tampered, content_type="application/json", HTTP_FLUTTERWAVE_SIGNATURE=good).status_code == 401
    assert anon.post(HOOK, raw, content_type="application/json", HTTP_FLUTTERWAVE_SIGNATURE=other_key).status_code == 401
    assert anon.post(HOOK, raw, content_type="application/json", HTTP_FLUTTERWAVE_SIGNATURE=good).status_code == 200


def test_signatures_are_compared_in_constant_time(client_for, fw):
    raw = json.dumps({"data": {"tx_ref": "not-ours"}}).encode()
    signature = base64.b64encode(hmac.new(SECRET.encode(), raw, hashlib.sha256).digest()).decode()
    with mock.patch.object(flutterwave.hmac, "compare_digest", wraps=hmac.compare_digest) as compare:
        client_for().post(HOOK, raw, content_type="application/json", HTTP_VERIF_HASH="wrong")
        client_for().post(HOOK, raw, content_type="application/json", HTTP_FLUTTERWAVE_SIGNATURE=signature)
    assert compare.call_count >= 2


# --- S5: replays ------------------------------------------------------------------------------


def test_a_replayed_webhook_is_acknowledged_but_not_acted_on(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/55/verify"] = verified(payment, transaction_id=55)
    body = {"event": "charge.completed", "data": {"id": 55, "tx_ref": payment.reference, "status": "successful"}}
    anon = client_for()
    assert anon.post(HOOK, body, format="json", HTTP_VERIF_HASH=SECRET).data == {"received": True}
    lycee.refresh_from_db()
    paid_until = lycee.paid_until
    for _ in range(4):
        response = anon.post(HOOK, body, format="json", HTTP_VERIF_HASH=SECRET)
        assert response.status_code == 200 and response.data == {"duplicate": True}
    assert len(verify_calls(fw)) == 1  # replays never reach Flutterwave
    lycee.refresh_from_db()
    assert lycee.paid_until == paid_until
    event = WebhookEvent.objects.get(signature_valid=True)
    assert event.outcome == "applied" and event.deliveries == 5 and event.payment_id == payment.pk
    assert len(audits("webhook_replayed")) == 4


def test_a_pending_event_sent_again_later_is_checked_again(client_for, lycee, lycee_admin, fw):
    """Flutterwave retries events it couldn't deliver; an event that wasn't final may be looked at again."""
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/60/verify"] = verified(payment, "pending", 60)
    body = {"event": "charge.completed", "data": {"id": 60, "tx_ref": payment.reference}}
    anon = client_for()
    assert anon.post(HOOK, body, format="json", HTTP_VERIF_HASH=SECRET).data == {"received": True}
    assert anon.post(HOOK, body, format="json", HTTP_VERIF_HASH=SECRET).data == {"duplicate": True}  # too soon
    assert len(verify_calls(fw)) == 1

    WebhookEvent.objects.filter(signature_valid=True).update(claimed_at=timezone.now() - webhooks.RETRY_AFTER * 2)
    fw["responses"]["/transactions/60/verify"] = verified(payment, "successful", 60)
    assert anon.post(HOOK, body, format="json", HTTP_VERIF_HASH=SECRET).data == {"received": True}
    payment.refresh_from_db()
    assert payment.status == "succeeded" and len(verify_calls(fw)) == 2


def test_an_event_that_hit_a_provider_outage_is_processed_when_retried(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")

    def down(path, payload):
        raise flutterwave.ProviderUnavailable()

    fw["responses"]["/transactions/61/verify"] = down
    body = {"event": "charge.completed", "data": {"id": 61, "tx_ref": payment.reference}}
    anon = client_for()
    assert anon.post(HOOK, body, format="json", HTTP_VERIF_HASH=SECRET).status_code == 503
    assert WebhookEvent.objects.get(signature_valid=True).outcome == "unavailable"
    WebhookEvent.objects.filter(signature_valid=True).update(claimed_at=timezone.now() - webhooks.RETRY_AFTER * 2)
    fw["responses"]["/transactions/61/verify"] = verified(payment, "successful", 61)
    assert anon.post(HOOK, body, format="json", HTTP_VERIF_HASH=SECRET).status_code == 200
    payment.refresh_from_db()
    assert payment.status == "succeeded"


def test_flooding_the_webhook_with_forgeries_cannot_fill_the_audit_log(client_for, fw, caplog):
    anon = client_for()
    with caplog.at_level(logging.WARNING, logger="apps.schools.webhooks"):
        for _ in range(webhooks.AUDITED_REFUSALS_PER_MINUTE + 10):
            assert anon.post(HOOK, {"data": {}}, format="json", HTTP_VERIF_HASH="x").status_code == 401
    assert len(audits("webhook_rejected")) == webhooks.AUDITED_REFUSALS_PER_MINUTE
    # ...but every one of them is still in the server log.
    refused = [r for r in caplog.records if "Refused a flutterwave webhook" in r.getMessage()]
    assert len(refused) == webhooks.AUDITED_REFUSALS_PER_MINUTE + 10


# --- S26: nothing is credited from a body or a redirect alone ---------------------------------


def test_a_webhook_body_claiming_success_is_not_believed(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/70/verify"] = verified(payment, "pending", 70)
    body = {
        "event": "charge.completed",
        "data": {"id": 70, "tx_ref": payment.reference, "status": "successful", "amount": 200, "currency": "USD"},
    }
    client_for().post(HOOK, body, format="json", HTTP_VERIF_HASH=SECRET)
    payment.refresh_from_db()
    lycee.refresh_from_db()
    assert payment.status == "pending" and lycee.paid_until is None


def test_a_webhook_naming_another_schools_transaction_is_not_applied(client_for, lycee, lycee_admin, fw):
    apade = make_school("APADE", "Kicukiro")
    ours = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    theirs = billing.start_payment(apade, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/71/verify"] = verified(theirs, "successful", 71)
    fw["responses"]["/transactions/verify_by_reference"] = {"status": "error", "message": "No transaction", "data": None}
    body = {"event": "charge.completed", "data": {"id": 71, "tx_ref": ours.reference, "status": "successful"}}
    client_for().post(HOOK, body, format="json", HTTP_VERIF_HASH=SECRET)
    ours.refresh_from_db()
    lycee.refresh_from_db()
    assert ours.status == "pending" and lycee.paid_until is None


def test_redirect_query_parameters_are_only_a_hint(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/72/verify"] = verified(payment, "failed", 72)
    fw["responses"]["/transactions/verify_by_reference"] = verified(payment, "pending", 72)
    tampered = {"transaction_id": "72", "status": "successful", "amount": "200", "currency": "USD", "months": 12}
    data = client_for(lycee_admin).post(f"/api/billing/payments/{payment.reference}/confirm/", tampered, format="json").data
    assert data["status"] == "pending" and data["months"] == 1
    lycee.refresh_from_db()
    assert lycee.paid_until is None


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"meta": {"school_id": "999999"}}, "school_mismatch"),
        ({"meta": [{"metaname": "school_id", "metavalue": "999999"}]}, "school_mismatch"),
        ({"currency": "RWF"}, "currency_mismatch"),
        ({"amount": "199.99"}, "amount_mismatch"),
        ({"amount": "Infinity"}, "amount_mismatch"),
        ({"amount": "NaN"}, "amount_mismatch"),
        ({"amount": None}, "amount_mismatch"),
    ],
)
def test_a_successful_transaction_that_does_not_match_is_refused_and_audited(client_for, lycee, lycee_admin, fw, change, reason):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    response = verified(payment, "successful", 80)
    response["data"].update(change)
    fw["responses"]["/transactions/verify_by_reference"] = response
    client = client_for(lycee_admin)
    assert client.post(f"/api/billing/payments/{payment.reference}/confirm/").data["status"] == "failed"
    client.post(f"/api/billing/payments/{payment.reference}/confirm/")  # asking again doesn't audit again
    lycee.refresh_from_db()
    assert lycee.paid_until is None and not LedgerEntry.objects.exists()
    assert [(a.details["reason"], a.details["transaction_id"]) for a in audits("payment_rejected")] == [(reason, "80")]


def test_the_payments_own_school_in_meta_is_accepted(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/verify_by_reference"] = verified(payment, "successful", 81, meta={"school_id": str(lycee.id)})
    assert client_for(lycee_admin).post(f"/api/billing/payments/{payment.reference}/confirm/").data["status"] == "succeeded"


def test_test_payments_are_never_confirmed_where_they_are_switched_off(client_for, lycee, lycee_admin, settings):
    settings.BILLING_DEV_MODE = False
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "dev")
    Payment.objects.filter(pk=payment.pk).update(provider_data={"dev_outcome": "success"})
    data = client_for(lycee_admin).post(f"/api/billing/payments/{payment.reference}/confirm/").data
    assert data["status"] == "pending"
    lycee.refresh_from_db()
    assert lycee.paid_until is None


# --- S31: one provider transaction, one payment -----------------------------------------------


def test_one_provider_transaction_cannot_pay_for_two_payments(client_for, lycee, lycee_admin, fw):
    first = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    second = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    assert billing.apply_payment(first, "777", {})
    lycee.refresh_from_db()
    paid_until = lycee.paid_until
    # A verification that (wrongly or maliciously) names the same transaction for another payment.
    with pytest.raises(billing.TransactionAlreadyUsed):
        billing.apply_payment(second, "777", {})
    fw["responses"]["/transactions/verify_by_reference"] = verified(second, "successful", 777)
    assert client_for(lycee_admin).post(f"/api/billing/payments/{second.reference}/confirm/").data["status"] == "pending"
    lycee.refresh_from_db()
    assert lycee.paid_until == paid_until
    assert [a.details["reason"] for a in audits("payment_rejected")] == ["transaction_reused"]
    # The database refuses it too.
    with pytest.raises(IntegrityError), transaction.atomic():
        Payment.objects.filter(pk=second.pk).update(provider_transaction_id="777")


# --- S15: prices come from the server ------------------------------------------------------------


def test_checkout_ignores_a_clients_amount_plan_and_duration(client_for, lycee, lycee_admin, fw):
    fw["responses"]["/payments"] = {"status": "success", "data": {"link": "https://checkout.flutterwave.com/pay/x"}}
    tampered = {
        "months": 12,
        "currency": "usd",
        "amount": "1",
        "price": "1",
        "total": "1",
        "plan": "free",
        "days": 9999,
        "period_end": "2099-01-01T00:00:00Z",
        "paid_until": "2099-01-01T00:00:00Z",
    }
    start = client_for(lycee_admin).post("/api/billing/checkout/", tampered, format="json")
    assert start.status_code == 201
    payment = Payment.objects.get(reference=start.data["reference"])
    assert (payment.amount, payment.currency, payment.months) == (Decimal("2400.00"), "USD", 12)
    sent = fw["calls"][0][2]
    assert sent["amount"] == "2400.00" and sent["currency"] == "USD"
    lycee.refresh_from_db()
    assert lycee.paid_until is None


@pytest.mark.parametrize(
    "body",
    [
        {"months": 2, "currency": "USD"},
        {"months": 0, "currency": "USD"},
        {"months": -1, "currency": "USD"},
        {"months": 13, "currency": "USD"},
        {"months": 1.5, "currency": "USD"},
        {"months": "12abc", "currency": "USD"},
        {"months": [12], "currency": "USD"},
        {"months": 10**9, "currency": "USD"},
        {"months": 1, "currency": "EUR"},
        {"months": 1, "currency": ""},
        {"months": 1, "currency": "US"},
        {"currency": "USD"},
    ],
)
def test_checkout_refuses_anything_not_on_the_price_list(client_for, lycee, lycee_admin, settings, body):
    settings.BILLING_DEV_MODE = True
    response = client_for(lycee_admin).post("/api/billing/checkout/", body, format="json")
    assert response.status_code == 400
    assert not Payment.objects.exists()


@pytest.mark.parametrize("bad_price", [Decimal("0"), Decimal("-200"), Decimal("NaN"), Decimal("Infinity")])
def test_a_misconfigured_price_never_becomes_a_free_checkout(client_for, lycee, lycee_admin, settings, bad_price):
    settings.BILLING_DEV_MODE = True
    settings.BILLING_PROVIDER = ""
    settings.SUBSCRIPTION_PRICES = {"USD": bad_price}
    response = client_for(lycee_admin).post("/api/billing/checkout/", {"months": 1, "currency": "USD"}, format="json")
    assert response.status_code == 503
    assert not Payment.objects.exists()


def test_a_price_cut_after_checkout_does_not_lower_what_is_owed(client_for, lycee, lycee_admin, fw, settings):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    settings.SUBSCRIPTION_PRICES = {"USD": Decimal("1")}
    fw["responses"]["/transactions/verify_by_reference"] = verified(payment, "successful", 90, amount="1.00")
    assert client_for(lycee_admin).post(f"/api/billing/payments/{payment.reference}/confirm/").data["status"] == "failed"


def test_test_checkout_ignores_a_clients_months_and_amount(client_for, lycee, lycee_admin, settings):
    settings.BILLING_DEV_MODE = True
    settings.BILLING_PROVIDER = ""
    client = client_for(lycee_admin)
    reference = client.post("/api/billing/checkout/", {"months": 1, "currency": "USD"}, format="json").data["reference"]
    done = client.post(
        f"/api/billing/dev/{reference}/complete/", {"outcome": "success", "months": 12, "amount": "0"}, format="json"
    ).data
    assert done["status"] == "succeeded" and done["months"] == 1 and done["amount"] == "200.00"


def test_nobody_can_set_a_subscription_date_or_status_by_editing_the_school(client_for, lycee, lycee_admin, staff):
    future = "2099-01-01T00:00:00Z"
    sneaky = {"paid_until": future, "status": "verified", "join_code": "AAAAAAAA", "subscription": {"paid_until": future}}
    assert client_for(lycee_admin).patch("/api/school/", {**sneaky, "phone": "+250700000000"}, format="json").status_code == 200
    assert client_for(staff).patch(f"/api/admin/schools/{lycee.id}/", sneaky, format="json").status_code == 200
    lycee.refresh_from_db()
    assert lycee.paid_until is None and lycee.join_code != "AAAAAAAA" and lycee.phone == "+250700000000"


@pytest.mark.parametrize(
    "body",
    [
        {"months": 0, "amount": "200", "currency": "USD", "note": "x"},
        {"months": 25, "amount": "200", "currency": "USD", "note": "x"},
        {"months": 1, "amount": "-1", "currency": "USD", "note": "x"},
        {"months": 1, "amount": "NaN", "currency": "USD", "note": "x"},
        {"months": 1, "amount": "Infinity", "currency": "USD", "note": "x"},
        {"months": 1, "amount": "200", "currency": "EUR", "note": "x"},
        {"months": 1, "amount": "200", "currency": "USD", "note": "   "},
    ],
)
def test_recorded_payments_are_validated(client_for, lycee, staff, body):
    assert client_for(staff).post(f"/api/admin/schools/{lycee.id}/payments/", body, format="json").status_code == 400
    lycee.refresh_from_db()
    assert lycee.paid_until is None


# --- S31: a bank transfer is recorded once ----------------------------------------------------------


def test_a_resent_manual_payment_request_records_nothing_new(client_for, lycee, staff):
    body = {"months": 1, "amount": "200", "currency": "USD", "note": "Bank of Kigali", "external_reference": "BK-4471"}
    client = client_for(staff)
    url = f"/api/admin/schools/{lycee.id}/payments/"
    first = client.post(url, body, format="json", HTTP_IDEMPOTENCY_KEY="record-0001-abcd")
    again = client.post(url, body, format="json", HTTP_IDEMPOTENCY_KEY="record-0001-abcd")
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.data["reference"] == again.data["reference"]
    assert Payment.objects.count() == 1 and LedgerEntry.objects.count() == 1
    assert len(audits("manual_payment")) == 1
    # The same key for a different payment is a mistake, not a replay.
    other = {**body, "months": 3, "external_reference": "BK-9999"}
    assert client.post(url, other, format="json", HTTP_IDEMPOTENCY_KEY="record-0001-abcd").status_code == 409
    assert client.post(url, other, format="json", HTTP_IDEMPOTENCY_KEY="bad key!").status_code == 400


def test_the_same_bank_reference_cannot_be_recorded_twice(client_for, lycee, staff):
    apade = make_school("APADE", "Kicukiro")
    client = client_for(staff)
    body = {"months": 1, "amount": "200", "currency": "USD", "note": "Bank of Kigali", "external_reference": "bk 4471"}
    assert client.post(f"/api/admin/schools/{lycee.id}/payments/", body, format="json").status_code == 201
    lycee.refresh_from_db()
    paid_until = lycee.paid_until
    for school, reference in ((lycee, "BK 4471"), (apade, "  bk   4471 ")):
        again = client.post(f"/api/admin/schools/{school.id}/payments/", {**body, "external_reference": reference}, format="json")
        assert again.status_code == 400 and "external_reference" in again.data
    lycee.refresh_from_db()
    apade.refresh_from_db()
    assert lycee.paid_until == paid_until and apade.paid_until is None
    assert Payment.objects.get().external_reference == "BK 4471"
