"""Choosing a school, school administration, paying, webhooks and reminders."""

from datetime import timedelta
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
    response = register(
        client_for(),
        role="school_admin",
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
    response = register(client_for(), role="school_admin", school=lycee.id, school_code=lycee.join_code)
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
    responses = {}

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
    fw["responses"]["/transactions/verify_by_reference"] = {
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
        client_for(), role="school_admin", new_school={"name": "GS Kimironko", "district": "Gasabo", "phone": "1"}
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
