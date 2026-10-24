"""Consent to the Terms and Privacy Policy, "Download my data", "Delete my account", erasure and retention.

Rwanda's Law N° 058/2021 gives everyone the right to see, correct and erase their personal data. These tests
hold Iga to what its Privacy Policy promises: registration needs consent, a new version is accepted again,
the download holds the user's own data from every app, a deletion can be cancelled for a while and then
leaves nothing personal behind (money records stay, pointing at an anonymised row), and old records go.
"""

import importlib
import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.apps import apps
from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.db import models
from django.utils import timezone

from apps.accounts import password_reset, privacy
from apps.accounts.models import ParentInvite, ParentLink, User
from apps.assessments.models import Answer, Attempt
from apps.classroom.models import Assignment, Classroom, Enrollment
from apps.coderun.models import CodeRunUsage
from apps.community.models import GroupMembership, Message, MessageReport, SharedNote, StudyGroup
from apps.core.models import AuditLog
from apps.core.retention import purge_expired
from apps.curriculum.models import LessonProgress
from apps.gamification.models import Badge, UserBadge, XPEvent
from apps.schools import billing, ledger
from apps.schools.models import LedgerEntry, Payment
from apps.simulations.models import Simulation, SimulationView
from apps.tutor.models import SantaUsage, TutorExchange
from apps.website.models import ContactMessage

from .conftest import add_mcq, make_quiz, make_school, make_user

pytestmark = pytest.mark.django_db
PASSWORD = "Str0ng-pass-123"


@pytest.fixture(autouse=True)
def _inline_background_work(monkeypatch):
    """Emails sent after the answer (password_reset.deliver) run at once, so the tests can read them."""
    monkeypatch.setattr(password_reset, "deliver", lambda work, *args: work(*args))


def register(client, **extra):
    payload = {"username": "newkid", "password": PASSWORD, "first_name": "New", "grade": "S1", **extra}
    return client.post("/api/auth/register/", payload, format="json")


def login(client, username, password=PASSWORD):
    return client.post("/api/auth/login/", {"identifier": username, "password": password}, format="json")


# --- Consent ---------------------------------------------------------------------------------------------


def test_registration_needs_the_terms_accepted(client_for):
    refused = register(client_for())
    assert refused.status_code == 400 and "accept_terms" in refused.data
    assert register(client_for(), accept_terms=False).status_code == 400
    assert not User.objects.filter(username="newkid").exists()


def test_registration_records_the_version_and_time_accepted(client_for):
    response = register(client_for(), accept_terms=True, terms_version=settings.LEGAL_VERSION)
    assert response.status_code == 201
    user = User.objects.get(username="newkid")
    assert user.terms_version == settings.LEGAL_VERSION
    assert abs((timezone.now() - user.terms_accepted_at).total_seconds()) < 60
    assert response.data["user"]["consent_required"] is False
    entry = AuditLog.objects.get(action="terms_accepted", target_id=str(user.pk))
    assert entry.details == {"version": settings.LEGAL_VERSION, "how": "register"}


def test_a_form_showing_older_texts_is_asked_to_read_them_again(client_for):
    response = register(client_for(), accept_terms=True, terms_version="2001-01-01")
    assert response.status_code == 400 and "terms_version" in response.data
    french = client_for().post(
        "/api/auth/register/",
        {"username": "x", "password": PASSWORD, "grade": "S1", "accept_terms": True, "terms_version": "old"},
        format="json",
        HTTP_ACCEPT_LANGUAGE="fr",
    )
    assert "viennent de changer" in str(french.data)


def test_a_new_version_is_accepted_again(client_for, student, settings):
    client = client_for(student)
    assert client.get("/api/auth/me/").data["consent_required"] is True  # never accepted (created before consent)
    assert client.post("/api/auth/accept-terms/", {"version": settings.LEGAL_VERSION}, format="json").status_code == 200
    assert client.get("/api/auth/me/").data["consent_required"] is False
    settings.LEGAL_VERSION = "2027-01-01"
    me = client.get("/api/auth/me/").data
    assert me["consent_required"] is True and me["terms_version"] != "2027-01-01"
    # Accepting the version the app showed before the change is refused: read the new one first.
    stale = client.post("/api/auth/accept-terms/", {"version": "2026-10-17"}, format="json")
    assert stale.status_code == 400
    assert client.post("/api/auth/accept-terms/", {"version": "2027-01-01"}, format="json").data["consent_required"] is False
    hows = list(AuditLog.objects.filter(action="terms_accepted").order_by("id").values_list("details__how", flat=True))
    assert hows == ["first_sign_in", "update"]


def test_a_roster_student_accepts_after_choosing_a_password(teacher, settings):
    from rest_framework.test import APIClient

    from apps.classroom.roster import create_accounts

    classroom = Classroom.objects.create(name="S2 A", grade="S2", teacher=teacher)
    row = {"line": 2, "first_name": "Keza", "last_name": "M", "username": "keza.m", "email": ""}
    temporary = create_accounts([row], classroom, teacher)[0]["temporary_password"]
    client = APIClient()
    signed_in = login(client, "keza.m", temporary)
    assert signed_in.data["user"]["must_change_password"] and signed_in.data["user"]["consent_required"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {signed_in.data['access']}")
    accept = {"version": settings.LEGAL_VERSION}
    # Until the temporary password is replaced nothing else is possible, accepting included...
    assert client.post("/api/auth/accept-terms/", accept, format="json").status_code == 403
    changed = client.post(
        "/api/auth/password/", {"current_password": temporary, "new_password": "My-own-pass-2026"}, format="json"
    )
    assert changed.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {changed.data['access']}")
    # ...then the app asks for the Terms and Privacy Policy before anything else.
    accepted = client.post("/api/auth/accept-terms/", accept, format="json")
    assert accepted.status_code == 200 and accepted.data["consent_required"] is False


# --- Download my data ------------------------------------------------------------------------------------


@pytest.fixture
def rich_student(subject, unit, lesson, teacher):
    """A student with something in every app that keeps personal data."""
    pupil = make_user("pupil", first_name="Ineza", last_name="Mukamana")
    parent = make_user("mama", role=User.Role.PARENT, school=None, first_name="Mama")
    ParentLink.objects.create(parent=parent, student=pupil)
    ParentInvite.objects.create(student=pupil, code_hash="x" * 64, expires_at=timezone.now() + timedelta(days=3))
    LessonProgress.objects.create(user=pupil, lesson=lesson)
    sim = Simulation.objects.create(slug="waves", title="Waves", provider="builtin", provider_id="waves")
    SimulationView.objects.create(user=pupil, simulation=sim)
    question = add_mcq(subject, unit)
    quiz = make_quiz(subject, unit, [question], is_free=True)
    attempt = Attempt.objects.create(user=pupil, quiz=quiz, status="marked", score=Decimal("1"), max_score=Decimal("1"))
    Answer.objects.create(attempt=attempt, question=question, text_answer="PUPIL-ANSWER")
    classroom = Classroom.objects.create(name="S2 Maths", grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=pupil)
    group = StudyGroup.objects.create(name="Revision", created_by=pupil)
    GroupMembership.objects.create(group=group, user=pupil, role=GroupMembership.Role.OWNER)
    Message.objects.create(group=group, author=pupil, body="PUPIL-CHAT-MESSAGE")
    SharedNote.objects.create(group=group, author=pupil, title="Notes", body="PUPIL-NOTE")
    XPEvent.objects.create(user=pupil, amount=10, reason="lesson", reference="lesson:1")
    badge = Badge.objects.create(code="first", name="First steps", description="x")
    UserBadge.objects.create(user=pupil, badge=badge)
    TutorExchange.objects.create(user=pupil, message="PUPIL-SANTA-QUESTION", reply="An answer")
    SantaUsage.objects.create(user=pupil, day=timezone.localdate(), questions=1)
    CodeRunUsage.objects.create(user=pupil, day=timezone.localdate(), runs=2)
    ContactMessage.objects.create(name="Ineza", email="PUPIL@example.com", message="PUPIL-CONTACT-MESSAGE")
    return pupil


def test_download_my_data_holds_every_app_and_only_the_users_own_data(client_for, rich_student, other_student):
    TutorExchange.objects.create(user=other_student, message="SOMEONE-ELSES-QUESTION", reply="x")
    response = client_for(rich_student).get("/api/auth/my-data/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json; charset=utf-8"
    assert response["Content-Disposition"].startswith('attachment; filename="iga-my-data-')
    assert response["Cache-Control"] == "no-store"
    data = json.loads(response.content)
    assert list(data)[:2] == ["export", "accounts"]
    for label, _module in privacy.userdata_modules():
        assert label in data, label
    text = response.content.decode()
    for mine in (
        "Mukamana",
        "pupil@example.com",
        "PUPIL-CHAT-MESSAGE",
        "PUPIL-NOTE",
        "PUPIL-SANTA-QUESTION",
        "PUPIL-CONTACT-MESSAGE",
    ):
        assert mine in text, mine
    assert "SOMEONE-ELSES-QUESTION" not in text
    assert data["accounts"]["parents"] == [{"name": "Mama", "linked_at": data["accounts"]["parents"][0]["linked_at"]}]
    assert data["curriculum"]["lessons_completed"][0]["lesson"] == "linear"
    assert AuditLog.objects.filter(action="data_export", actor=rich_student).exists()


def test_download_my_data_needs_a_recent_password_check_and_is_limited(client_for, student, monkeypatch):
    stale = client_for(student, signed_in=False).get("/api/auth/my-data/")
    assert stale.status_code == 403 and stale.data["code"] == "step_up_required"
    assert client_for().get("/api/auth/my-data/").status_code == 401
    from rest_framework.throttling import SimpleRateThrottle

    from .conftest import RELAXED_RATES

    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RELAXED_RATES, "data_export": "2/hour"})
    client = client_for(student)
    assert [client.get("/api/auth/my-data/").status_code for _ in range(3)] == [200, 200, 429]


def test_every_export_is_plain_json(rich_student, teacher):
    for user in (rich_student, teacher):
        for label, module in privacy.userdata_modules():
            json.dumps(module.export_for(user))  # no datetimes or Decimals left: a TypeError would fail here
            assert isinstance(module.export_for(user), dict), label


# --- The convention --------------------------------------------------------------------------------------


def _user_foreign_keys():
    for model in apps.get_models():
        for field in model._meta.get_fields():
            if (
                isinstance(field, (models.ForeignKey, models.OneToOneField))
                and field.related_model is User
                and not field.auto_created
            ):
                yield model, field


def test_every_app_holding_user_rows_has_a_userdata_module():
    missing = set()
    for model, _field in _user_foreign_keys():
        config = apps.get_app_config(model._meta.app_label)
        if not config.name.startswith("apps."):
            continue
        try:
            module = importlib.import_module(f"{config.name}.userdata")
        except ModuleNotFoundError:
            missing.add(config.name)
            continue
        assert callable(module.export_for) and callable(module.erase_for), config.name
    assert not missing, f"Add a userdata module (export_for, erase_for) to: {sorted(missing)}"
    labels = [label for label, _module in privacy.userdata_modules()]
    assert labels[-1] == "accounts" and {"classroom", "assessments", "community", "tutor", "gamification", "schools"} <= set(
        labels
    )


# --- Delete my account -----------------------------------------------------------------------------------


def test_deleting_needs_a_recent_password_check_and_a_ticked_box(client_for, student):
    stale = client_for(student, signed_in=False).post("/api/auth/delete-account/", {"confirm": True}, format="json")
    assert stale.status_code == 403 and stale.data["code"] == "step_up_required"
    unticked = client_for(student).post("/api/auth/delete-account/", {"confirm": False}, format="json")
    assert unticked.status_code == 400
    assert client_for(student).post("/api/auth/delete-account/", {}, format="json").status_code == 400
    assert User.objects.get(pk=student.pk).deletion_due_at is None


def test_deleting_ends_every_session_and_signing_in_during_the_grace_period_cancels_it(student):
    from rest_framework.test import APIClient

    client, elsewhere = APIClient(), APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login(client, 'student').data['access']}")
    elsewhere.credentials(HTTP_AUTHORIZATION=f"Bearer {login(elsewhere, 'student').data['access']}")
    response = client.post("/api/auth/delete-account/", {"confirm": True}, format="json")
    assert response.status_code == 200, response.data
    student.refresh_from_db()
    due = student.deletion_due_at
    assert (due - student.deletion_requested_at).days == settings.ACCOUNT_DELETION_GRACE_DAYS
    assert response.cookies[settings.REFRESH_COOKIE_NAME].value == ""  # signed out here
    assert elsewhere.get("/api/auth/me/").status_code == 401  # and everywhere else
    assert client.get("/api/auth/me/").status_code == 401
    assert AuditLog.objects.filter(action="account_deletion_requested", actor=student).exists()
    assert "deleted" in mail.outbox[0].subject and student.email in mail.outbox[0].to

    # Signing in keeps the account.
    again = login(APIClient(), "student")
    assert again.status_code == 200 and again.data["deletion_cancelled"] is True
    assert again.data["user"]["deletion_due_at"] is None
    student.refresh_from_db()
    assert student.deletion_due_at is None and student.deletion_requested_at is None
    assert "deletion_cancelled" not in login(APIClient(), "student").data
    call_command("privacy_cleanup")
    assert User.objects.get(pk=student.pk).erased_at is None


def test_the_iga_team_and_the_last_school_administrator_cannot_delete_themselves(client_for, admin_user):
    refused = client_for(admin_user).post("/api/auth/delete-account/", {"confirm": True}, format="json")
    assert refused.status_code == 409 and refused.data["code"] == "platform_admin"
    school = make_school("GS Remera", "Gasabo", paid_until=timezone.now() + timedelta(days=30))
    head = make_user("head", role=User.Role.SCHOOL_ADMIN, school=school)
    refused = client_for(head).post("/api/auth/delete-account/", {"confirm": True}, format="json")
    assert refused.status_code == 409 and refused.data["code"] == "transfer_school_first"
    assert "GS Remera" in refused.data["detail"]
    # Once another administrator is approved, the first may go.
    make_user("deputy", role=User.Role.SCHOOL_ADMIN, school=school)
    assert client_for(head).post("/api/auth/delete-account/", {"confirm": True}, format="json").status_code == 200


def _ask_and_expire(client_for, user):
    assert client_for(user).post("/api/auth/delete-account/", {"confirm": True}, format="json").status_code == 200
    User.objects.filter(pk=user.pk).update(deletion_due_at=timezone.now() - timedelta(minutes=1))


def test_erasure_leaves_nothing_personal_behind(client_for, rich_student, other_student):
    pupil = rich_student
    login(client_for(), "pupil")  # an audit entry with the username and address
    group = StudyGroup.objects.get(name="Revision")
    GroupMembership.objects.create(group=group, user=other_student)
    reported = Message.objects.create(group=group, author=pupil, body="REPORTED-MESSAGE")
    MessageReport.objects.create(message=reported, reporter=other_student, reason="rude")
    _ask_and_expire(client_for, pupil)
    mail.outbox.clear()

    call_command("privacy_cleanup")

    pupil.refresh_from_db()
    assert pupil.erased_at is not None and not pupil.is_active and not pupil.has_usable_password()
    assert pupil.username == f"deleted-{pupil.pk}" and pupil.email is None
    assert (pupil.first_name, pupil.last_name, pupil.avatar, pupil.school_id, pupil.xp) == ("", "", {}, None, 0)
    assert pupil.display_name == "Deleted account" and pupil.short_name == "Deleted account"
    for model in (LessonProgress, SimulationView, Attempt, XPEvent, UserBadge, TutorExchange, SantaUsage, CodeRunUsage):
        assert not model.objects.filter(user=pupil).exists(), model
    assert not Enrollment.objects.filter(student=pupil).exists()
    assert not ParentLink.objects.filter(student=pupil).exists() and not ParentInvite.objects.filter(student=pupil).exists()
    assert not GroupMembership.objects.filter(user=pupil).exists()
    assert not SharedNote.objects.filter(author=pupil).exists()
    assert not ContactMessage.objects.exists()
    # The group lives on with its other member as owner; the reported message stays for the moderators.
    assert GroupMembership.objects.get(group=group).role == GroupMembership.Role.OWNER
    assert list(Message.objects.filter(author=pupil).values_list("body", flat=True)) == ["REPORTED-MESSAGE"]
    # The audit log keeps what happened, without the username or address.
    for entry in AuditLog.objects.filter(actor=pupil):
        assert entry.ip_address is None and "username" not in entry.details, entry.action
    assert AuditLog.objects.filter(action="account_erased", target_id=str(pupil.pk)).exists()
    # The old password and name sign in to nothing.
    assert login(client_for(), "pupil").status_code == 401
    assert "deleted" in mail.outbox[0].subject and mail.outbox[0].to == ["pupil@example.com"]
    # Running again changes nothing.
    assert privacy.erase_due_accounts() == 0


# Rows that may still point at an erased account: the anonymised reference that records others rely on
# (money, teaching material, other students' work and marks, moderation, accountability).
ALLOWED_REFERENCES = {
    ("schools.payment", "created_by"),
    ("schools.school", "created_by"),
    ("schools.school", "verified_by"),
    ("curriculum.lesson", "author"),
    ("curriculum.resource", "uploaded_by"),
    ("assessments.question", "author"),
    ("assessments.quiz", "author"),
    ("assessments.answer", "marked_by"),
    ("classroom.classroom", "teacher"),
    ("classroom.assignment", "created_by"),
    ("community.studygroup", "created_by"),
    ("community.message", "author"),
    ("community.message", "hidden_by"),
    ("community.messagereport", "reporter"),
    ("community.messagereport", "resolved_by"),
    ("core.auditlog", "actor"),
    ("accounts.user", "school_approved_by"),
    ("accounts.parentinvite", "used_by"),
    ("website.contactmessage", "handled_by"),
    ("admin.logentry", "user"),
}


def test_only_anonymised_references_remain_after_erasure(client_for, rich_student, teacher, subject, unit):
    # A teacher with a class, an assignment, authored material and marks, then erased.
    classroom = Classroom.objects.get(name="S2 Maths")
    Assignment.objects.create(classroom=classroom, title="Homework", created_by=teacher)
    Answer.objects.filter(attempt__user=rich_student).update(marked_by=teacher)
    for user in (rich_student, teacher):
        privacy.erase_user(user)
    left = []
    for model, field in _user_foreign_keys():
        key = (model._meta.label_lower, field.name)
        for user in (rich_student, teacher):
            if model.objects.filter(**{field.name: user}).exists() and key not in ALLOWED_REFERENCES:
                left.append(key)
    assert not left, f"Rows still pointing at an erased account (erase them, or add them to ALLOWED_REFERENCES): {left}"
    # A teacher's classes are archived, not deleted, so their students keep their history.
    classroom.refresh_from_db()
    assert classroom.archived and classroom.teacher_id == teacher.pk
    assert Assignment.objects.filter(classroom=classroom).exists()


def test_money_is_never_deleted(client_for, admin_user):
    school = make_school("GS Kacyiru", "Gasabo")
    head = make_user("bursar", role=User.Role.SCHOOL_ADMIN, school=school)
    make_user("deputy2", role=User.Role.SCHOOL_ADMIN, school=school)
    payment = billing.record_manual_payment(school, head, 1, Decimal("200"), "USD", "Bank transfer")
    entries = list(LedgerEntry.objects.values_list("sequence", "entry_hash"))
    assert entries
    _ask_and_expire(client_for, head)
    call_command("privacy_cleanup")
    head.refresh_from_db()
    assert head.erased_at is not None
    assert Payment.objects.get(pk=payment.pk).created_by_id == head.pk  # the anonymised reference
    assert list(LedgerEntry.objects.values_list("sequence", "entry_hash")) == entries
    assert ledger.verify().ok
    exported = privacy.export_user_data(admin_user)
    assert exported["schools"]["payments_made"] == []


# --- Retention -------------------------------------------------------------------------------------------


def test_old_records_are_deleted_and_recent_ones_kept(student, settings):
    now = timezone.now()
    old, recent = now - timedelta(days=800), now - timedelta(days=5)
    for when in (old, recent):
        exchange = TutorExchange.objects.create(user=student, message="q", reply="a")
        TutorExchange.objects.filter(pk=exchange.pk).update(created_at=when)
        entry = AuditLog.objects.create(action="login", target_type="")
        AuditLog.objects.filter(pk=entry.pk).update(created_at=when)
        message = ContactMessage.objects.create(name="n", email="n@example.com", message="hello there")
        ContactMessage.objects.filter(pk=message.pk).update(created_at=when)
        SantaUsage.objects.create(user=student, day=timezone.localdate(when))
        CodeRunUsage.objects.create(user=student, day=timezone.localdate(when))
    deleted = purge_expired(now)
    assert deleted["santa_exchanges"] == deleted["audit_entries"] == deleted["contact_messages"] == 1
    assert deleted["santa_usage"] == deleted["code_run_usage"] == 1
    for model in (TutorExchange, AuditLog, ContactMessage, SantaUsage, CodeRunUsage):
        assert model.objects.count() == 1, model
    # 0 keeps them.
    settings.SANTA_LOG_RETENTION_DAYS = 0
    TutorExchange.objects.update(created_at=old)
    assert "santa_exchanges" not in purge_expired(now) and TutorExchange.objects.count() == 1


def test_the_site_information_states_the_periods(client_for, settings):
    data = client_for().get("/api/site/").data
    assert data["retention"]["deletion_grace_days"] == settings.ACCOUNT_DELETION_GRACE_DAYS == 14
    assert data["retention"]["santa_days"] == settings.SANTA_LOG_RETENTION_DAYS
    assert data["legal"]["version"] == settings.LEGAL_VERSION and data["legal"]["draft"] is True
