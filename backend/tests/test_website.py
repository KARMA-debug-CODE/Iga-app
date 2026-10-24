"""The public site: site information, the contact form, robots.txt and the sitemap, maintenance mode and the
friendly answer to an unexpected error."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts import password_reset
from apps.core import maintenance
from apps.core.models import AuditLog
from apps.website.models import ContactMessage

from .conftest import RELAXED_RATES, make_user

pytestmark = pytest.mark.django_db
PASSWORD = "Str0ng-pass-123"
MESSAGE = {"name": "Jean Bosco", "email": "Head@GS-Remera.rw", "school": "GS Remera", "message": "We would like a demo."}


@pytest.fixture(autouse=True)
def _inline_background_work(monkeypatch):
    monkeypatch.setattr(password_reset, "deliver", lambda work, *args: work(*args))


# --- Site information ----------------------------------------------------------------------------------


def test_site_information_is_public_and_comes_from_the_settings(settings):
    settings.SUBSCRIPTION_PRICES = {"USD": Decimal("150"), "RWF": Decimal("200000")}
    settings.LEGAL_DRAFT_NOTICE = False
    settings.PRIVACY_CONTACT_EMAIL = "dpo@school.rw"
    data = APIClient().get("/api/site/").json()
    assert data["pricing"] == {"prices": {"USD": "150", "RWF": "200000"}, "month_options": [1, 3, 6, 12], "grace_days": 3}
    assert data["legal"]["draft"] is False and data["legal"]["privacy_email"] == "dpo@school.rw"
    assert data["maintenance"] is False
    # The same price list as the school's billing page (never written down twice).
    from apps.schools.billing import price_list

    assert data["pricing"] == price_list()


def test_site_information_answers_even_with_a_broken_token():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")
    assert client.get("/api/site/").status_code == 200


# --- Contact form --------------------------------------------------------------------------------------


def test_a_visitor_can_write_and_the_message_is_kept_and_emailed(settings, django_capture_on_commit_callbacks):
    settings.CONTACT_EMAIL = "hello@iga.rw"
    with django_capture_on_commit_callbacks(execute=True):
        response = APIClient().post("/api/contact/", MESSAGE, format="json", HTTP_ACCEPT_LANGUAGE="fr")
    assert response.status_code == 201 and "Merci" in response.json()["detail"]
    message = ContactMessage.objects.get()
    assert (message.name, message.email, message.school, message.language) == (
        "Jean Bosco",
        "head@gs-remera.rw",
        "GS Remera",
        "fr",
    )
    assert message.user is None
    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == ["hello@iga.rw"] and sent.reply_to == ["head@gs-remera.rw"] and "We would like a demo." in sent.body
    assert AuditLog.objects.filter(action="contact_message").exists()


def test_without_a_contact_address_messages_are_only_kept(settings):
    settings.CONTACT_EMAIL = ""
    assert APIClient().post("/api/contact/", MESSAGE, format="json").status_code == 201
    assert ContactMessage.objects.count() == 1 and not mail.outbox


def test_a_signed_in_sender_is_recorded(client_for, student):
    assert client_for(student).post("/api/contact/", MESSAGE, format="json").status_code == 201
    assert ContactMessage.objects.get().user == student


@pytest.mark.parametrize(
    "change, field",
    [
        ({"name": ""}, "name"),
        ({"email": "not-an-email"}, "email"),
        ({"message": "Hi"}, "message"),
        ({"message": "x" * 5001}, "message"),
        ({"name": "​‮"}, "name"),
        ({"name": ["a list"]}, "name"),
    ],
)
def test_contact_messages_are_validated(change, field):
    response = APIClient().post("/api/contact/", {**MESSAGE, **change}, format="json")
    assert response.status_code == 400 and field in response.json()
    assert not ContactMessage.objects.exists()


def test_contact_text_is_cleaned_before_it_is_kept():
    dirty = {**MESSAGE, "name": "Jean​  ‮Bosco", "message": "Hello\u0000"}
    assert APIClient().post("/api/contact/", dirty, format="json").status_code == 400  # a NUL is refused outright
    dirty["message"] = "Hello​ there,\r\n<script>alert(1)</script>"
    assert APIClient().post("/api/contact/", dirty, format="json").status_code == 201
    message = ContactMessage.objects.get()
    assert message.name == "Jean Bosco"
    assert message.message == "Hello there,\n<script>alert(1)</script>"  # kept as typed text, never rendered as HTML


def test_robots_that_fill_the_hidden_field_are_thanked_and_ignored(settings):
    settings.CONTACT_EMAIL = "hello@iga.rw"
    response = APIClient().post("/api/contact/", {**MESSAGE, "website": "http://spam.example"}, format="json")
    assert response.status_code == 201
    assert not ContactMessage.objects.exists() and not mail.outbox
    assert AuditLog.objects.filter(action="contact_spam").exists()


def test_the_contact_form_is_limited_per_address(monkeypatch):
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RELAXED_RATES, "contact": "2/hour"})
    client = APIClient(REMOTE_ADDR="10.7.7.7")
    assert [client.post("/api/contact/", MESSAGE, format="json").status_code for _ in range(3)] == [201, 201, 429]
    assert APIClient(REMOTE_ADDR="10.7.7.8").post("/api/contact/", MESSAGE, format="json").status_code == 201


def test_platform_admins_read_and_handle_messages(client_for, admin_user, student):
    APIClient().post("/api/contact/", MESSAGE, format="json")
    message = ContactMessage.objects.get()
    admin = client_for(admin_user)
    listed = admin.get("/api/admin/contact/").json()
    assert listed["count"] == 1 and listed["results"][0]["email"] == "head@gs-remera.rw"
    handled = admin.post(f"/api/admin/contact/{message.id}/handle/", {"handled": True}, format="json").json()
    assert handled["handled_at"] and handled["handled_by"]
    assert admin.get("/api/admin/contact/").json()["count"] == 0
    assert admin.get("/api/admin/contact/?status=handled").json()["count"] == 1
    assert admin.get("/api/admin/contact/?status=all").json()["count"] == 1
    admin.post(f"/api/admin/contact/{message.id}/handle/", {"handled": False}, format="json")
    assert admin.get("/api/admin/contact/").json()["count"] == 1
    assert list(AuditLog.objects.filter(target_type="website.contactmessage").values_list("action", flat=True)) == [
        "contact_reopened",
        "contact_handled",
        "contact_message",
    ]
    # Nobody else reads them, and the team confirms its password first.
    assert client_for(student).get("/api/admin/contact/").status_code == 403
    stale = client_for(admin_user, signed_in=False).get("/api/admin/contact/")
    assert stale.status_code == 403 and stale.json()["code"] == "step_up_required"


# --- robots.txt and the sitemap ------------------------------------------------------------------------


def test_robots_txt_keeps_crawlers_to_the_public_pages(settings):
    settings.FRONTEND_URL = "https://iga.example.rw"
    response = APIClient().get("/robots.txt", HTTP_ACCEPT="text/html")
    assert response.status_code == 200 and response["Content-Type"] == "text/plain; charset=utf-8"
    text = response.content.decode()
    assert "Disallow: /api/" in text and "Disallow: /profile" in text and "Allow: /terms" in text
    assert "Sitemap: https://iga.example.rw/sitemap.xml" in text


def test_the_sitemap_lists_only_public_pages(settings):
    settings.FRONTEND_URL = "https://iga.example.rw"
    response = APIClient().get("/sitemap.xml", HTTP_ACCEPT="application/json")
    assert response.status_code == 200 and response["Content-Type"] == "application/xml; charset=utf-8"
    text = response.content.decode()
    for page in ("", "/register", "/contact", "/terms", "/privacy"):
        assert f"<loc>https://iga.example.rw{page or '/'}</loc>" in text
    assert "/profile" not in text and "/admin" not in text and "/api/" not in text
    assert f"<lastmod>{settings.LEGAL_VERSION}</lastmod>" in text


# --- Maintenance mode ----------------------------------------------------------------------------------


@pytest.fixture
def maintenance_file(tmp_path, settings):
    settings.MAINTENANCE_FILE = str(tmp_path / "maintenance" / "on")
    return tmp_path / "maintenance" / "on"


def _token_client(username):
    client = APIClient()
    response = client.post("/api/auth/login/", {"identifier": username, "password": PASSWORD}, format="json")
    assert response.status_code == 200, response.json()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
    return client, response


def test_the_command_switches_maintenance_on_and_off(maintenance_file, capsys):
    call_command("maintenance", "on")
    assert maintenance_file.exists() and maintenance.maintenance_on()
    call_command("maintenance")
    assert "Maintenance mode is on." in capsys.readouterr().out
    call_command("maintenance", "off")
    assert not maintenance_file.exists() and not maintenance.maintenance_on()


def test_during_maintenance_everyone_but_the_iga_team_gets_back_soon(maintenance_file, student, admin_user):
    pupil, _ = _token_client("student")
    team, signed_in = _token_client("admin")
    assert signed_in.cookies[maintenance.TEAM_COOKIE].value == "1"  # nginx lets the team through
    maintenance.set_maintenance(True)
    refused = pupil.get("/api/dashboard/")
    assert refused.status_code == 503 and refused.json()["code"] == "maintenance"
    assert int(refused["Retry-After"]) > 0
    french = pupil.get("/api/subjects/", HTTP_ACCEPT_LANGUAGE="fr")
    assert "mise à jour" in french.json()["detail"]
    assert team.get("/api/dashboard/").status_code == 200
    assert APIClient().post("/api/auth/register/", {}, format="json").status_code == 503
    # Still open: health checks, the site information, payment webhooks.
    assert APIClient().get("/api/health/").status_code == 200
    assert APIClient().get("/api/site/").json()["maintenance"] is True
    assert APIClient().post("/api/billing/webhooks/flutterwave/", {}, format="json").status_code != 503
    maintenance.set_maintenance(False)
    assert pupil.get("/api/dashboard/").status_code == 200


def test_during_maintenance_only_the_team_signs_in_or_refreshes(maintenance_file, student, admin_user):
    pupil = APIClient()
    pupil.post("/api/auth/login/", {"identifier": "student", "password": PASSWORD}, format="json")
    maintenance.set_maintenance(True)
    refused = APIClient().post("/api/auth/login/", {"identifier": "student", "password": PASSWORD}, format="json")
    assert refused.status_code == 503 and "access" not in refused.json()
    # A wrong password is still just wrong (nothing new is learnt about the account).
    wrong = APIClient().post("/api/auth/login/", {"identifier": "student", "password": "nope"}, format="json")
    assert wrong.status_code == 401
    assert pupil.post("/api/auth/refresh/").status_code == 503
    team = APIClient().post("/api/auth/login/", {"identifier": "admin", "password": PASSWORD}, format="json")
    assert team.status_code == 200 and team.cookies[maintenance.TEAM_COOKIE].value == "1"
    maintenance.set_maintenance(False)
    # The student's session was kept for afterwards.
    assert pupil.post("/api/auth/refresh/").status_code == 200


def test_the_team_cookie_is_only_for_platform_admins(student, admin_user):
    client = APIClient()
    client.cookies[maintenance.TEAM_COOKIE] = "1"  # left on a shared computer, or made up
    response = client.post("/api/auth/login/", {"identifier": "student", "password": PASSWORD}, format="json")
    assert response.cookies[maintenance.TEAM_COOKIE].value == ""  # removed
    logged_out = APIClient()
    logged_out.cookies[maintenance.TEAM_COOKIE] = "1"
    assert logged_out.post("/api/auth/logout/").cookies[maintenance.TEAM_COOKIE].value == ""


@override_settings(MAINTENANCE_MODE=True)
def test_the_setting_turns_maintenance_on_too(student):
    assert APIClient().get("/api/meta/").status_code == 503
    assert APIClient().get("/api/health/").status_code == 200


# --- Unexpected errors ---------------------------------------------------------------------------------


def test_an_unexpected_error_is_a_short_friendly_answer(student, monkeypatch, client_for):
    from apps.core import views

    def broken(*args, **kwargs):
        raise RuntimeError("database exploded: secret detail")

    monkeypatch.setattr(views, "level_from_xp", broken)
    client = client_for(student)
    client.raise_request_exception = False
    response = client.get("/api/dashboard/", HTTP_ACCEPT_LANGUAGE="fr")
    assert response.status_code == 500
    assert response.json() == {
        "detail": "Un problème est survenu de notre côté. Réessayez dans quelques minutes.",
        "code": "server_error",
    }
    assert "secret detail" not in response.content.decode()


def test_deletion_grace_period_setting_is_respected(client_for, student, settings):
    settings.ACCOUNT_DELETION_GRACE_DAYS = 3
    response = client_for(student).post("/api/auth/delete-account/", {"confirm": True}, format="json")
    student.refresh_from_db()
    assert response.status_code == 200
    assert student.deletion_due_at - student.deletion_requested_at == timedelta(days=3)
    assert "3" in response.json()["detail"]


def test_a_school_admin_whose_school_is_not_verified_can_leave(client_for):
    from apps.schools.models import School

    pending = School.objects.create(name="New school", district="Huye")
    head = make_user("newhead", role="school_admin", school=pending)
    assert client_for(head).post("/api/auth/delete-account/", {"confirm": True}, format="json").status_code == 200
