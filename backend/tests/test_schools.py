"""Choosing a school, school administration, paying, webhooks and reminders."""

from datetime import UTC, timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.schools import billing, flutterwave
from apps.schools.access import content_access
from apps.schools.models import BillingReminder, Payment, School

from .conftest import make_school, make_user

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"


@pytest.fixture
def lycee(db):
    return make_school("Lycée de Kigali", "Nyarugenge")


@pytest.fixture
def lycee_admin(lycee):
    return make_user("lkadmin", role="school_admin", school=lycee)


@pytest.fixture
def apade(db):
    return make_school("APADE", "Kicukiro")


def register(client, **data):
    payload = {"username": "newkid", "password": PASSWORD, "first_name": "New", "grade": "S2"}
    payload.update(data)
    return client.post("/api/auth/register/", payload, format="json")


# --- Finding and joining ------------------------------------------------------------


def test_directory_lists_verified_schools_only(client_for, lycee):
    make_school("Lycée Notre-Dame", "Huye", status="pending")
    client = client_for()
    assert client.get("/api/schools/", {"q": "l"}).data == []  # at least two letters
    names = [s["name"] for s in client.get("/api/schools/", {"q": "lycée"}).data]
    assert names == ["Lycée de Kigali"]
    assert client.get("/api/schools/", {"district": "Nyarugenge"}).data[0]["province"] == "Kigali City"
    assert len(client.get("/api/schools/districts/").data) == 5


def test_register_with_the_school_code_is_approved_at_once(client_for, lycee):
    response = register(client_for(), school=lycee.id, school_code=lycee.join_code.lower())
    assert response.status_code == 201, response.data
    user = User.objects.get(username="newkid")
    assert user.school == lycee and user.school_status == "approved"
    assert response.data["user"]["school"]["name"] == "Lycée de Kigali"


def test_register_without_code_waits_for_approval(client_for, lycee):
    response = register(client_for(), school=lycee.id)
    assert response.status_code == 201
    assert User.objects.get(username="newkid").school_status == "pending"
    assert response.data["user"]["access"] == {"premium": False, "reason": "pending_approval"}


def test_wrong_code_creates_nothing(client_for, lycee):
    response = register(client_for(), school=lycee.id, school_code="WRONG123")
    assert response.status_code == 400 and "school_code" in response.data
    assert not User.objects.filter(username="newkid").exists()


def test_cannot_pick_an_unverified_school(client_for):
    pending = make_school("Pending School", "Huye", status="pending")
    assert register(client_for(), school=pending.id).status_code == 400


def test_school_admin_registers_a_new_school(client_for):
    no_email = register(client_for(), role="school_admin", new_school={"name": "GS Remera", "district": "Gasabo", "phone": "1"})
    assert no_email.status_code == 400 and "email" in no_email.data
    response = register(
        client_for(),
        role="school_admin",
        email="head@gsremera.rw",
        new_school={"name": "  GS   Remera ", "district": "Gasabo", "phone": "+250788000000"},
    )
    assert response.status_code == 201, response.data
    school = School.objects.get(name="GS Remera")
    assert school.status == "pending" and school.created_by.username == "newkid"
    assert User.objects.get(username="newkid").school_status == "pending"
    # The same school can't be registered twice.
    again = register(
        client_for(), username="other", role="school_admin", new_school={"name": "gs remera", "district": "Gasabo", "phone": "1"}
    )
    assert again.status_code == 400


def test_school_admins_cannot_join_by_code(client_for, lycee):
    response = register(client_for(), role="school_admin", email="a@b.rw", school=lycee.id, school_code=lycee.join_code)
    assert response.status_code == 400


def test_parents_do_not_join_schools(client_for, lycee):
    assert register(client_for(), role="parent", school=lycee.id).status_code == 400


def test_choosing_and_changing_school(client_for, lycee):
    other = make_school("APADE", "Kicukiro")
    user = make_user("mover", school=None)
    client = client_for(user)
    data = client.post("/api/my-school/", {"school": lycee.id, "school_code": lycee.join_code}, format="json").data
    assert data["school_status"] == "approved"
    data = client.post("/api/my-school/", {"school": other.id}, format="json").data
    assert data["school_status"] == "pending" and data["school"]["name"] == "APADE"
    assert client.delete("/api/my-school/").data["school"] is None


def test_school_codes_cannot_be_guessed_quickly(client_for, lycee, monkeypatch):
    from rest_framework.throttling import SimpleRateThrottle

    from .conftest import RELAXED_RATES

    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RELAXED_RATES, "join": "3/min"})
    client = client_for(make_user("guesser", school=None))
    for _ in range(3):
        client.post("/api/my-school/", {"school": lycee.id, "school_code": "AAAAAAAA"}, format="json")
    assert client.post("/api/my-school/", {"school": lycee.id, "school_code": lycee.join_code}, format="json").status_code == 429


# --- The school administrator ----------------------------------------------------------


def test_school_admin_approves_students_and_teachers(client_for, lycee, lycee_admin):
    pupil = make_user("pupil", school=None)
    teacher = make_user("newteacher", role="teacher", school=None)
    for user in (pupil, teacher):
        user.school, user.school_status = lycee, "pending"
        user.save()
    client = client_for(lycee_admin)
    pending = client.get("/api/school/members/", {"status": "pending"}).data
    assert {m["username"] for m in pending} == {"pupil", "newteacher"}
    client.post("/api/school/members/decide/", {"ids": [pupil.id, teacher.id], "approve": True}, format="json")
    pupil.refresh_from_db()
    teacher.refresh_from_db()
    assert pupil.school_status == "approved" and pupil.school_approved_by == lycee_admin
    assert teacher.teacher_approved  # the school vouches for its own teachers


def test_school_admin_cannot_touch_other_schools(client_for, lycee, lycee_admin):
    other = make_school("APADE", "Kicukiro")
    stranger = make_user("stranger", school=other)
    stranger.school_status = "pending"
    stranger.save()
    client = client_for(lycee_admin)
    client.post("/api/school/members/decide/", {"ids": [stranger.id], "approve": True}, format="json")
    stranger.refresh_from_db()
    assert stranger.school_status == "pending"
    assert client.post(f"/api/school/members/{stranger.id}/remove/").status_code == 404


def test_pending_school_admins_have_no_powers(client_for, lycee):
    hopeful = make_user("hopeful", role="school_admin", school=lycee)
    hopeful.school_status = "pending"
    hopeful.save()
    assert client_for(hopeful).get("/api/school/").status_code == 403


def test_remove_member_and_new_code(client_for, lycee, lycee_admin):
    pupil = make_user("pupil", school=lycee)
    client = client_for(lycee_admin)
    assert client.post(f"/api/school/members/{pupil.id}/remove/").status_code == 204
    pupil.refresh_from_db()
    assert pupil.school is None
    old = lycee.join_code
    new = client.post("/api/school/new-code/").data["join_code"]
    assert new != old and len(new) == 8


def test_school_admin_edits_contacts_but_not_name(client_for, lycee, lycee_admin):
    client = client_for(lycee_admin)
    data = client.patch("/api/school/", {"phone": "+250 788 123 456", "name": "Renamed"}, format="json").data
    lycee.refresh_from_db()
    assert lycee.phone == "+250 788 123 456" and lycee.name == "Lycée de Kigali"
    assert data["pricing"]["prices"] == {"USD": "200"}
    assert data["counts"]["admins"] == 1


# --- Paying with the development checkout ------------------------------------------------


def test_dev_checkout_pays_for_the_whole_school(client_for, lycee, lycee_admin, settings):
    settings.BILLING_DEV_MODE = True
    settings.BILLING_PROVIDER = ""
    pupil = make_user("pupil", school=lycee)
    assert not content_access(pupil).premium

    client = client_for(lycee_admin)
    start = client.post("/api/billing/checkout/", {"months": 3, "currency": "USD"}, format="json")
    assert start.status_code == 201, start.data
    reference = start.data["reference"]
    assert start.data["checkout_url"].endswith(f"/school/billing/dev-checkout?ref={reference}")
    assert Payment.objects.get(reference=reference).amount == Decimal("600.00")

    done = client.post(f"/api/billing/dev/{reference}/complete/", {"outcome": "success"}, format="json").data
    assert done["status"] == "succeeded"
    lycee.refresh_from_db()
    assert lycee.paid_until > timezone.now() + timedelta(days=85)
    assert content_access(User.objects.get(pk=pupil.pk)).premium
    assert len(mail.outbox) == 1 and "payment received" in mail.outbox[0].subject

    # Confirming again changes nothing.
    paid_until = lycee.paid_until
    client.post(f"/api/billing/payments/{reference}/confirm/")
    lycee.refresh_from_db()
    assert lycee.paid_until == paid_until


def test_cancelled_dev_checkout(client_for, lycee, lycee_admin, settings):
    settings.BILLING_DEV_MODE = True
    client = client_for(lycee_admin)
    reference = client.post("/api/billing/checkout/", {"months": 1, "currency": "USD"}, format="json").data["reference"]
    done = client.post(f"/api/billing/dev/{reference}/complete/", {"outcome": "cancel"}, format="json").data
    assert done["status"] == "failed"
    lycee.refresh_from_db()
    assert lycee.paid_until is None


def test_dev_checkout_is_off_in_production(client_for, lycee, lycee_admin, settings):
    settings.BILLING_DEV_MODE = False
    settings.BILLING_PROVIDER = ""
    response = client_for(lycee_admin).post("/api/billing/checkout/", {"months": 1, "currency": "USD"}, format="json")
    assert response.status_code == 400
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "dev")
    assert (
        client_for(lycee_admin)
        .post(f"/api/billing/dev/{payment.reference}/complete/", {"outcome": "success"}, format="json")
        .status_code
        == 403
    )


def test_only_that_schools_admins_see_or_pay(client_for, lycee, lycee_admin, student, settings):
    settings.BILLING_DEV_MODE = True
    other_admin = make_user("otheradmin", role="school_admin", school=make_school("APADE", "Kicukiro"))
    reference = (
        client_for(lycee_admin).post("/api/billing/checkout/", {"months": 1, "currency": "USD"}, format="json").data["reference"]
    )
    assert client_for(other_admin).get(f"/api/billing/payments/{reference}/").status_code == 403
    assert (
        client_for(other_admin).post(f"/api/billing/dev/{reference}/complete/", {"outcome": "success"}, format="json").status_code
        == 403
    )
    assert client_for(student).post("/api/billing/checkout/", {"months": 1, "currency": "USD"}, format="json").status_code == 403


def test_invalid_checkout_options(client_for, lycee_admin, settings):
    settings.BILLING_DEV_MODE = True
    client = client_for(lycee_admin)
    assert client.post("/api/billing/checkout/", {"months": 2, "currency": "USD"}, format="json").status_code == 400
    assert client.post("/api/billing/checkout/", {"months": 1, "currency": "EUR"}, format="json").status_code == 400


# --- Flutterwave ------------------------------------------------------------------------


@pytest.fixture
def fw(settings, monkeypatch):
    settings.BILLING_PROVIDER = "flutterwave"
    settings.FLUTTERWAVE_SECRET_KEY = "FLWSECK_TEST-x"
    settings.FLUTTERWAVE_WEBHOOK_HASH = "webhook-secret"
    calls = []
    # The list of a reference's attempts (consulted when the lookup by reference shows a failure).
    responses = {"/transactions?": {"status": "success", "data": []}}

    def fake_request(method, path, payload=None):
        calls.append((method, path, payload))
        for prefix, body in responses.items():
            if path.startswith(prefix):
                return body(path, payload) if callable(body) else body
        raise AssertionError(f"unexpected call {method} {path}")

    monkeypatch.setattr(flutterwave, "_request", fake_request)
    return {"calls": calls, "responses": responses}


def test_flutterwave_checkout_and_redirect_confirmation(client_for, lycee, lycee_admin, fw):
    fw["responses"]["/payments"] = {"status": "success", "data": {"link": "https://checkout.flutterwave.com/v3/hosted/pay/abc"}}
    client = client_for(lycee_admin)
    start = client.post("/api/billing/checkout/", {"months": 1, "currency": "USD"}, format="json").data
    assert start["checkout_url"] == "https://checkout.flutterwave.com/v3/hosted/pay/abc"
    method, path, payload = fw["calls"][0]
    assert (method, path) == ("POST", "/payments")
    assert payload["tx_ref"] == start["reference"] and payload["amount"] == "200.00" and payload["currency"] == "USD"
    assert payload["redirect_url"].endswith(f"/school/billing/return?ref={start['reference']}")
    assert payload["session_duration"] == 60 and payload["max_retry_attempt"] == 5
    assert "phonenumber" not in payload["customer"]  # the school gave no phone: don't send null

    fw["responses"]["/transactions/verify_by_reference"] = {
        "status": "success",
        "data": {"id": 987, "tx_ref": start["reference"], "status": "successful", "amount": 200, "currency": "USD"},
    }
    confirmed = client.post(f"/api/billing/payments/{start['reference']}/confirm/").data
    assert confirmed["status"] == "succeeded"
    assert Payment.objects.get(reference=start["reference"]).provider_transaction_id == "987"


def test_flutterwave_amount_or_currency_mismatch_is_refused(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/verify_by_reference"] = {
        "status": "success",
        "data": {"id": 1, "tx_ref": payment.reference, "status": "successful", "amount": 2, "currency": "USD"},
    }
    data = client_for(lycee_admin).post(f"/api/billing/payments/{payment.reference}/confirm/").data
    assert data["status"] == "failed"
    lycee.refresh_from_db()
    assert lycee.paid_until is None


def test_flutterwave_webhook(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    body = {
        "event": "charge.completed",
        "data": {"id": 55, "tx_ref": payment.reference, "status": "successful", "amount": 999999},
    }
    fw["responses"]["/transactions/55/verify"] = {
        "status": "success",
        "data": {"id": 55, "tx_ref": payment.reference, "status": "successful", "amount": "200.00", "currency": "USD"},
    }
    anon = client_for()
    url = "/api/billing/webhooks/flutterwave/"
    assert anon.post(url, body, format="json").status_code == 401
    assert anon.post(url, body, format="json", HTTP_VERIF_HASH="wrong").status_code == 401
    assert anon.post(url, body, format="json", HTTP_VERIF_HASH="webhook-secret").status_code == 200
    lycee.refresh_from_db()
    first = lycee.paid_until
    assert first is not None
    # Flutterwave retries: a second delivery doesn't add another month.
    anon.post(url, body, format="json", HTTP_VERIF_HASH="webhook-secret")
    lycee.refresh_from_db()
    assert lycee.paid_until == first
    # Unknown references are acknowledged and ignored.
    other = {"event": "charge.completed", "data": {"tx_ref": "not-ours"}}
    assert anon.post(url, other, format="json", HTTP_VERIF_HASH="webhook-secret").data == {"ignored": True}


def test_flutterwave_hmac_signature(client_for, lycee, lycee_admin, fw):
    import base64
    import hashlib
    import hmac
    import json

    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/verify_by_reference"] = {"status": "success", "data": {"status": "pending"}}
    raw = json.dumps({"event": "charge.completed", "data": {"tx_ref": payment.reference}}).encode()
    signature = base64.b64encode(hmac.new(b"webhook-secret", raw, hashlib.sha256).digest()).decode()
    response = client_for().post(
        "/api/billing/webhooks/flutterwave/", raw, content_type="application/json", HTTP_FLUTTERWAVE_SIGNATURE=signature
    )
    assert response.status_code == 200
    payment.refresh_from_db()
    assert payment.status == "pending"  # still pending at Flutterwave: nothing applied


def _verify_response(payment, status, transaction_id=1, amount="200.00", currency="USD"):
    return {
        "status": "success",
        "data": {"id": transaction_id, "tx_ref": payment.reference, "status": status, "amount": amount, "currency": currency},
    }


def test_a_declined_card_then_a_successful_retry_is_applied(client_for, lycee, lycee_admin, fw):
    """Flutterwave's page lets the payer try again with the same reference after a decline."""
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    client = client_for(lycee_admin)
    confirm = f"/api/billing/payments/{payment.reference}/confirm/"
    fw["responses"]["/transactions/verify_by_reference"] = _verify_response(payment, "failed", 10)
    assert client.post(confirm).data["status"] == "pending"  # the checkout is still open

    fw["responses"]["/transactions/11/verify"] = _verify_response(payment, "successful", 11)
    data = client.post(confirm, {"transaction_id": "11"}, format="json").data
    assert data["status"] == "succeeded"
    lycee.refresh_from_db()
    assert lycee.paid_until is not None
    assert Payment.objects.get(pk=payment.pk).provider_transaction_id == "11"


def test_a_success_reported_after_the_payment_was_closed_still_counts(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    Payment.objects.filter(pk=payment.pk).update(created_at=timezone.now() - timedelta(hours=3))
    fw["responses"]["/transactions/verify_by_reference"] = _verify_response(payment, "failed", 20)
    client = client_for(lycee_admin)
    assert client.post(f"/api/billing/payments/{payment.reference}/confirm/").data["status"] == "failed"

    # A late webhook for a successful attempt: the money arrived, so the school gets its month.
    fw["responses"]["/transactions/21/verify"] = _verify_response(payment, "successful", 21)
    body = {"event": "charge.completed", "data": {"id": 21, "tx_ref": payment.reference, "status": "successful"}}
    hook = client_for().post("/api/billing/webhooks/flutterwave/", body, format="json", HTTP_VERIF_HASH="webhook-secret")
    assert hook.status_code == 200
    payment.refresh_from_db()
    lycee.refresh_from_db()
    assert payment.status == "succeeded" and lycee.paid_until is not None
    first = lycee.paid_until
    # And never twice.
    client_for().post("/api/billing/webhooks/flutterwave/", body, format="json", HTTP_VERIF_HASH="webhook-secret")
    lycee.refresh_from_db()
    assert lycee.paid_until == first


def test_a_transaction_for_another_reference_is_not_applied(client_for, lycee, lycee_admin, apade, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    other = billing.start_payment(apade, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/30/verify"] = _verify_response(other, "successful", 30)
    fw["responses"]["/transactions/verify_by_reference"] = {
        "status": "error",
        "message": "No transaction was found",
        "data": None,
    }
    data = (
        client_for(lycee_admin)
        .post(f"/api/billing/payments/{payment.reference}/confirm/", {"transaction_id": "30"}, format="json")
        .data
    )
    assert data["status"] == "pending"
    lycee.refresh_from_db()
    assert lycee.paid_until is None


def test_form_encoded_and_legacy_webhooks_are_understood(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/40/verify"] = _verify_response(payment, "pending", 40)
    url = "/api/billing/webhooks/flutterwave/"
    anon = client_for()
    # Flutterwave's default: form-encoded. Legacy (v2) bodies are flat, with txRef.
    form = f"txRef={payment.reference}&id=40&status=pending"
    response = anon.post(url, form, content_type="application/x-www-form-urlencoded", HTTP_VERIF_HASH="webhook-secret")
    assert response.data == {"received": True}
    nested = f"event=charge.completed&data[tx_ref]={payment.reference}&data[id]=40"
    response = anon.post(url, nested, content_type="application/x-www-form-urlencoded", HTTP_VERIF_HASH="webhook-secret")
    assert response.data == {"received": True}
    assert [c[1] for c in fw["calls"]].count("/transactions/40/verify") == 2
    # Nothing to go on: acknowledged (so it isn't retried) and logged.
    response = anon.post(url, {"event": "charge.completed"}, format="json", HTTP_VERIF_HASH="webhook-secret")
    assert response.data == {"ignored": True}
    bad = anon.post(url, "{not json", content_type="application/json", HTTP_VERIF_HASH="webhook-secret")
    assert bad.status_code == 400


def test_mobile_money_is_charged_in_whole_francs(client_for, lycee, lycee_admin, fw, settings):
    settings.SUBSCRIPTION_PRICES = {"USD": Decimal("200"), "RWF": Decimal("265000.40")}
    lycee.phone = "+250788000000"
    lycee.save()
    fw["responses"]["/payments"] = {"status": "success", "data": {"link": "https://checkout.flutterwave.com/v3/hosted/pay/rwf"}}
    start = client_for(lycee_admin).post("/api/billing/checkout/", {"months": 3, "currency": "RWF"}, format="json").data
    payload = fw["calls"][0][2]
    assert payload["amount"] == "795001" and payload["currency"] == "RWF"
    assert "mobilemoneyrwanda" in payload["payment_options"]
    assert payload["customer"]["phonenumber"] == "+250788000000"
    assert Payment.objects.get(reference=start["reference"]).amount == Decimal("795001")


def test_reconcile_applies_lost_webhooks_and_closes_abandoned_checkouts(lycee, lycee_admin, apade, fw):
    from apps.schools.management.commands.reconcile_payments import reconcile

    paid = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    abandoned = billing.start_payment(apade, lycee_admin, 1, "USD", "flutterwave")
    still_open = billing.start_payment(apade, lycee_admin, 3, "USD", "flutterwave")
    ancient = billing.start_payment(apade, lycee_admin, 1, "USD", "flutterwave")
    now = timezone.now()
    Payment.objects.filter(pk=abandoned.pk).update(created_at=now - timedelta(hours=2))
    Payment.objects.filter(pk=ancient.pk).update(created_at=now - timedelta(days=10))

    def by_reference(path, payload):
        if paid.reference in path:
            return _verify_response(paid, "successful", 50)
        return {"status": "error", "message": "No transaction was found", "data": None}

    fw["responses"]["/transactions/verify_by_reference"] = by_reference
    counts = reconcile(now)
    statuses = dict(Payment.objects.values_list("reference", "status"))
    assert statuses[paid.reference] == "succeeded"
    assert statuses[abandoned.reference] == "cancelled"
    assert statuses[still_open.reference] == "pending"  # its checkout may still be in use
    assert statuses[ancient.reference] == "cancelled"
    assert counts["expired"] == 1 and counts["succeeded"] == 1
    lycee.refresh_from_db()
    assert lycee.paid_until is not None

    # The provider is down: nothing changes, and the next run tries again.
    def down(path, payload):
        raise flutterwave.ProviderUnavailable()

    fw["responses"]["/transactions/verify_by_reference"] = down
    assert reconcile(now)["unreachable"] == 1  # the open payment; the closed one was asked about a moment ago
    assert reconcile(now + timedelta(minutes=61))["unreachable"] == 2  # an hour later, the closed one too
    assert Payment.objects.get(pk=still_open.pk).status == "pending"


def test_flutterwave_outage_cancels_the_checkout(client_for, lycee_admin, fw):
    def down(path, payload):
        raise flutterwave.ProviderUnavailable()

    fw["responses"]["/payments"] = down
    response = client_for(lycee_admin).post("/api/billing/checkout/", {"months": 1, "currency": "USD"}, format="json")
    assert response.status_code == 503
    assert Payment.objects.get().status == "cancelled"


# --- Platform administrators --------------------------------------------------------------


def test_platform_admin_verifies_school_and_its_first_admin(client_for, admin_user):
    response = register(
        client_for(),
        role="school_admin",
        email="head@kimironko.rw",
        new_school={"name": "GS Kimironko", "district": "Gasabo", "phone": "1"},
    )
    school = School.objects.get(name="GS Kimironko")
    listed = client_for(admin_user).get("/api/admin/schools/", {"status": "pending"}).data
    assert [s["name"] for s in listed] == ["GS Kimironko"]
    client_for(admin_user).post(f"/api/admin/schools/{school.id}/verify/")
    school.refresh_from_db()
    creator = User.objects.get(username=response.data["user"]["username"])
    assert school.status == "verified" and creator.school_status == "approved"
    assert creator.managed_school == school


def test_platform_admin_records_bank_transfer(client_for, admin_user, lycee, lycee_admin):
    response = client_for(admin_user).post(
        f"/api/admin/schools/{lycee.id}/payments/",
        {"months": 12, "amount": "2400", "currency": "USD", "note": "Bank of Kigali ref 4471"},
        format="json",
    )
    assert response.status_code == 201
    lycee.refresh_from_db()
    assert lycee.subscription_active()
    stats = client_for(admin_user).get("/api/admin/stats/").data["subscriptions"]
    assert stats["all_time"] == {"USD": "2400.00"} and stats["active_schools"] == 1
    payments = client_for(lycee_admin).get("/api/school/payments/").data
    assert payments[0]["note"] == "Bank of Kigali ref 4471"


def test_suspending_a_school_removes_access(client_for, admin_user):
    school = make_school("Paid", "Huye", paid_until=timezone.now() + timedelta(days=30))
    pupil = make_user("pupil", school=school)
    assert content_access(pupil).premium
    client_for(admin_user).post(f"/api/admin/schools/{school.id}/suspend/")
    assert not content_access(User.objects.get(pk=pupil.pk)).premium


def test_non_admins_cannot_use_platform_endpoints(client_for, lycee_admin, lycee):
    assert client_for(lycee_admin).get("/api/admin/schools/").status_code == 403
    assert client_for(lycee_admin).post(f"/api/admin/schools/{lycee.id}/verify/").status_code == 403


# --- Reminders ---------------------------------------------------------------------------------


def test_reminders_are_sent_once_per_stage(lycee, lycee_admin):
    lycee.paid_until = timezone.now() + timedelta(days=6, hours=12)
    lycee.save()
    call_command("billing_reminders")
    call_command("billing_reminders")
    assert len(mail.outbox) == 1 and "7 day" in mail.outbox[0].subject
    lycee.paid_until = timezone.now() - timedelta(hours=2)
    lycee.save()
    call_command("billing_reminders")
    assert len(mail.outbox) == 2 and "has ended" in mail.outbox[1].subject
    assert BillingReminder.objects.count() == 2


def test_no_reminders_far_from_the_end_date(lycee, lycee_admin):
    lycee.paid_until = timezone.now() + timedelta(days=20)
    lycee.save()
    call_command("billing_reminders")
    assert mail.outbox == []


# --- Review fixes: payments ---------------------------------------------------------------


def test_a_good_card_after_a_declined_one_is_found_once_the_checkout_closed(lycee, lycee_admin, fw):
    """The lookup by reference may return the declined attempt; the successful one must still count."""
    from apps.schools.management.commands.reconcile_payments import reconcile

    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    Payment.objects.filter(pk=payment.pk).update(created_at=timezone.now() - timedelta(minutes=80))
    fw["responses"]["/transactions/verify_by_reference"] = _verify_response(payment, "failed", 10)
    fw["responses"]["/transactions?"] = {
        "status": "success",
        "data": [
            {"id": 10, "tx_ref": payment.reference, "status": "failed"},
            {"id": 11, "tx_ref": payment.reference, "status": "successful"},
            {"id": 12, "tx_ref": "someone-else", "status": "successful"},
        ],
    }
    fw["responses"]["/transactions/11/verify"] = _verify_response(payment, "successful", 11)
    reconcile()
    payment.refresh_from_db()
    lycee.refresh_from_db()
    assert payment.status == "succeeded" and payment.provider_transaction_id == "11"
    assert lycee.paid_until is not None
    assert not any(path.startswith("/transactions/12") for _, path, _ in fw["calls"])


def test_reconcile_rechecks_payments_closed_in_the_last_day(lycee, lycee_admin, fw):
    from apps.schools.management.commands.reconcile_payments import reconcile

    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    Payment.objects.filter(pk=payment.pk).update(created_at=timezone.now() - timedelta(hours=5), status="cancelled")
    fw["responses"]["/transactions/verify_by_reference"] = _verify_response(payment, "successful", 60)
    reconcile()
    payment.refresh_from_db()
    assert payment.status == "succeeded"
    old = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    Payment.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=2), status="cancelled")
    calls = len(fw["calls"])
    reconcile()
    assert len(fw["calls"]) == calls  # older closed payments are left alone


def test_reconcile_leaves_final_payments_alone(lycee, lycee_admin, fw):
    from apps.schools.management.commands.reconcile_payments import reconcile

    wrong_amount = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    never_started = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    closed = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    earlier = timezone.now() - timedelta(hours=2)
    Payment.objects.filter(pk=wrong_amount.pk).update(
        created_at=earlier, status="failed", provider_data={"status": "successful", "amount": 2}
    )
    Payment.objects.filter(pk=never_started.pk).update(
        created_at=earlier, status="cancelled", provider_data={"checkout_failed": True}
    )
    Payment.objects.filter(pk=closed.pk).update(created_at=earlier, status="cancelled")
    fw["responses"]["/transactions/verify_by_reference"] = {
        "status": "error",
        "message": "No transaction was found",
        "data": None,
    }
    reconcile()
    asked = [path for _, path, _ in fw["calls"]]
    assert any(closed.reference in path for path in asked)
    assert not any(wrong_amount.reference in path or never_started.reference in path for path in asked)


def test_a_pending_attempt_does_not_hide_a_successful_one(lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")
    fw["responses"]["/transactions/verify_by_reference"] = _verify_response(payment, "pending", 10)
    fw["responses"]["/transactions?"] = {
        "status": "success",
        "data": [
            {"id": 10, "tx_ref": payment.reference, "status": "pending"},
            {"id": 11, "tx_ref": payment.reference, "status": "successful"},
        ],
    }
    fw["responses"]["/transactions/11/verify"] = _verify_response(payment, "successful", 11)
    from apps.schools import providers

    assert providers.get("flutterwave").verify(payment).status == "succeeded"


def test_checkout_that_never_started_is_marked(client_for, lycee_admin, fw):
    def down(path, payload):
        raise flutterwave.ProviderUnavailable()

    fw["responses"]["/payments"] = down
    client_for(lycee_admin).post("/api/billing/checkout/", {"months": 1, "currency": "USD"}, format="json")
    assert Payment.objects.get().provider_data == {"checkout_failed": True}


def _http_error(code, body):
    import io
    import urllib.error

    return urllib.error.HTTPError("https://api.flutterwave.com/v3/x", code, "error", {}, io.BytesIO(body.encode()))


@pytest.mark.parametrize(
    ("failure", "unavailable"),
    [
        ("503-json", True),
        ("429-json", True),
        ("401-json", True),
        ("400-json", False),  # e.g. "no transaction found": an answer, not an outage
        ("reset", True),
        ("disconnected", True),
        ("garbled", True),
    ],
)
def test_flutterwave_failures_are_never_read_as_answers(failure, unavailable, settings, monkeypatch):
    import http.client
    import urllib.request

    settings.FLUTTERWAVE_SECRET_KEY = "FLWSECK_TEST-x"

    class Garbled:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"<html>gateway</html>"

    def fake_urlopen(request, timeout=None):
        if failure.endswith("-json"):
            raise _http_error(int(failure[:3]), '{"status": "error", "message": "nope", "data": null}')
        if failure == "reset":
            raise ConnectionResetError("reset by peer")
        if failure == "disconnected":
            raise http.client.RemoteDisconnected("closed")
        return Garbled()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    if unavailable:
        with pytest.raises(flutterwave.ProviderUnavailable):
            flutterwave._request("GET", "/transactions/1/verify")
    else:
        assert flutterwave._request("GET", "/transactions/1/verify")["status"] == "error"


def test_webhook_asks_flutterwave_to_retry_when_its_api_is_down(client_for, lycee, lycee_admin, fw):
    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "flutterwave")

    def down(path, payload):
        raise flutterwave.ProviderUnavailable()

    fw["responses"]["/transactions/77/verify"] = down
    body = {"event": "charge.completed", "data": {"id": 77, "tx_ref": payment.reference}}
    response = client_for().post("/api/billing/webhooks/flutterwave/", body, format="json", HTTP_VERIF_HASH="webhook-secret")
    assert response.status_code == 503  # Flutterwave retries later
    assert Payment.objects.get(pk=payment.pk).status == "pending"


def test_months_are_counted_in_kigali_time(lycee, lycee_admin):
    from datetime import datetime

    payment = billing.start_payment(lycee, lycee_admin, 1, "USD", "dev")
    # 1 March 2026, 01:00 in Kigali is still 28 February in UTC.
    billing.apply_payment(payment, now=datetime(2026, 2, 28, 23, 0, tzinfo=UTC))
    lycee.refresh_from_db()
    end = timezone.localtime(lycee.paid_until)
    assert (end.year, end.month, end.day, end.hour) == (2026, 4, 1, 1)


def test_reminders_tell_the_truth_about_the_grace_period(lycee, lycee_admin, settings):
    from apps.schools.management.commands.billing_reminders import due_reminders

    settings.SUBSCRIPTION_GRACE_DAYS = 3
    now = timezone.now()
    lycee.paid_until = now - timedelta(hours=1)
    assert due_reminders(lycee, now) == "expired"
    lycee.paid_until = now - timedelta(days=4)
    assert due_reminders(lycee, now) == "access_ended"
    lycee.paid_until = now - timedelta(days=30)
    assert due_reminders(lycee, now) is None

    lycee.paid_until = now - timedelta(hours=1)
    lycee.save()
    call_command("billing_reminders")
    assert "keep full access until" in mail.outbox[-1].body
    lycee.paid_until = now - timedelta(days=4)
    lycee.save()
    call_command("billing_reminders")
    assert "now only see the free lessons" in mail.outbox[-1].body


def test_manual_payment_receipts_do_not_name_the_iga_staff_member(client_for, admin_user, lycee, lycee_admin):
    client_for(admin_user).post(
        f"/api/admin/schools/{lycee.id}/payments/",
        {"months": 1, "amount": "200", "currency": "USD", "note": "Bank ref 123"},
        format="json",
    )
    payment = client_for(lycee_admin).get("/api/school/payments/").data[0]
    assert payment["provider"] == "manual" and payment["paid_by"] is None


# --- Review fixes: membership -------------------------------------------------------------


def test_a_suspended_schools_admin_has_no_powers(client_for, admin_user, lycee, lycee_admin):
    teacher = make_user("newteacher", role="teacher", school=None)
    client_for(teacher).post("/api/my-school/", {"school": lycee.id}, format="json")
    client_for(admin_user).post(f"/api/admin/schools/{lycee.id}/suspend/")
    admin = client_for(User.objects.get(pk=lycee_admin.pk))
    assert admin.get("/api/school/").status_code == 403
    assert admin.post("/api/school/members/decide/", {"ids": [teacher.id], "approve": True}, format="json").status_code == 403
    assert admin.post("/api/school/new-code/").status_code == 403
    teacher.refresh_from_db()
    assert teacher.teacher_approved is False


def test_teacher_approval_from_a_school_ends_when_they_leave_it(client_for, lycee, lycee_admin):
    teacher = make_user("newteacher", role="teacher", school=None)
    client_for(teacher).post("/api/my-school/", {"school": lycee.id}, format="json")
    admin = client_for(lycee_admin)
    admin.post("/api/school/members/decide/", {"ids": [teacher.id], "approve": True}, format="json")
    teacher.refresh_from_db()
    assert teacher.teacher_approved and teacher.teacher_approved_by_school_id == lycee.id
    assert admin.post(f"/api/school/members/{teacher.id}/remove/").status_code == 204
    teacher.refresh_from_db()
    assert teacher.teacher_approved is False and teacher.can_teach is False
    # A teacher the Iga team approved keeps that approval whatever school they join or leave.
    approved = make_user("igateacher", role="teacher", teacher_approved=True, school=lycee)
    admin.post(f"/api/school/members/{approved.id}/remove/")
    approved.refresh_from_db()
    assert approved.teacher_approved is True


def test_a_school_cannot_undo_the_iga_teams_withdrawal(client_for, admin_user, lycee, lycee_admin):
    teacher = make_user("flagged", role="teacher", teacher_approved=True, school=None)
    client_for(admin_user).patch(f"/api/admin/users/{teacher.id}/", {"teacher_approved": False}, format="json")
    client_for(teacher).post("/api/my-school/", {"school": lycee.id}, format="json")
    client_for(lycee_admin).post("/api/school/members/decide/", {"ids": [teacher.id], "approve": True}, format="json")
    teacher.refresh_from_db()
    assert teacher.school_status == "approved"  # still a member of the school...
    assert teacher.teacher_approved is False and teacher.teacher_revoked is True  # ...but not a teacher


def test_a_school_confirms_teachers_who_joined_with_the_code(client_for, lycee, lycee_admin):
    teacher = make_user("coded", role="teacher", school=None)
    client_for(teacher).post("/api/my-school/", {"school": lycee.id, "school_code": lycee.join_code}, format="json")
    teacher.refresh_from_db()
    assert teacher.school_status == "approved" and teacher.teacher_approved is False
    admin = client_for(lycee_admin)
    member = next(m for m in admin.get("/api/school/members/").data if m["id"] == teacher.id)
    assert member["needs_teacher_confirmation"] is True
    changed = admin.post("/api/school/members/decide/", {"ids": [teacher.id], "approve": True}, format="json").data
    teacher.refresh_from_db()
    assert teacher.teacher_approved is True and changed
    member = next(m for m in admin.get("/api/school/members/").data if m["id"] == teacher.id)
    assert member["needs_teacher_confirmation"] is False


def test_choosing_your_own_school_again_keeps_you_approved(client_for, lycee, student):
    client = client_for(student)
    client.post("/api/my-school/", {"school": lycee.id, "school_code": lycee.join_code}, format="json")
    assert client.post("/api/my-school/", {"school": lycee.id}, format="json").data["school_status"] == "approved"


def test_a_squatted_school_name_can_be_rejected(client_for, admin_user):
    def register(username):
        return client_for().post(
            "/api/auth/register/",
            {
                "username": username,
                "password": "Str0ng-pass-123",
                "email": f"{username}@example.com",
                "role": "school_admin",
                "new_school": {"name": "GS Remera", "district": "Gasabo", "phone": "+250788000000"},
            },
            format="json",
        )

    assert register("squatter").status_code == 201
    second = register("realhead")
    assert second.status_code == 400 and "waiting for the Iga team" in str(second.data)
    school = School.objects.get(name="GS Remera")
    platform = client_for(admin_user)
    assert platform.post(f"/api/admin/schools/{school.id}/reject/").status_code == 204
    squatter = User.objects.get(username="squatter")
    assert squatter.school_id is None and squatter.school_status == ""
    assert register("realhead").status_code == 201
    verified = make_school("Verified", "Huye")
    assert platform.post(f"/api/admin/schools/{verified.id}/reject/").status_code == 400


def test_renaming_a_school_onto_another_is_refused(client_for, admin_user, lycee):
    other = make_school("APADE", "Nyarugenge")
    response = client_for(admin_user).patch(f"/api/admin/schools/{other.id}/", {"name": "lycée de kigali"}, format="json")
    assert response.status_code == 400


def test_admins_of_a_deleted_school_can_choose_another(client_for, lycee):
    stray = make_school("Duplicate", "Huye")
    admin = make_user("strayadmin", role="school_admin", school=stray)
    stray.delete()
    admin = User.objects.get(pk=admin.pk)
    assert admin.school_id is None and admin.school_status == ""
    assert client_for(admin).post("/api/my-school/", {"school": lycee.id}, format="json").status_code == 200


def test_school_admins_keep_an_email(client_for, lycee_admin):
    response = client_for(lycee_admin).patch("/api/auth/me/", {"email": ""}, format="json")
    assert response.status_code == 400


def test_seed_demo_can_run_again_after_the_pending_admin_left(client_for):
    import io

    call_command("seed_demo", force=True, stdout=io.StringIO())
    gsadmin = User.objects.get(username="gsadmin")
    assert client_for(gsadmin).delete("/api/my-school/").status_code == 200
    call_command("seed_demo", force=True, stdout=io.StringIO())
    gsadmin.refresh_from_db()
    assert gsadmin.school.name == "GS Remera Catholique" and gsadmin.school_status == "pending"
    assert School.objects.filter(name="GS Remera Catholique").count() == 1


def test_upgrade_marks_teacher_confirmations_made_by_schools(lycee, lycee_admin, admin_user):
    import importlib

    from django.apps import apps as registry

    migration = importlib.import_module("apps.accounts.migrations.0008_mark_school_teacher_confirmations")
    by_school = make_user("byschool", role="teacher", teacher_approved=True, school=lycee)
    User.objects.filter(pk=by_school.pk).update(school_approved_by=lycee_admin)
    by_iga = make_user("byiga", role="teacher", teacher_approved=True, school=lycee)
    User.objects.filter(pk=by_iga.pk).update(school_approved_by=admin_user)
    by_code = make_user("bycode", role="teacher", teacher_approved=True, school=lycee)
    migration.mark_school_confirmations(registry, None)
    assert User.objects.get(pk=by_school.pk).teacher_approved_by_school_id == lycee.id
    assert User.objects.get(pk=by_iga.pk).teacher_approved_by_school_id is None
    assert User.objects.get(pk=by_code.pk).teacher_approved_by_school_id is None
