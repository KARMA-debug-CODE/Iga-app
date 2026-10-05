"""The backend speaks the reader's language: English by default, French when the app asks for it."""

import re
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from django.core import mail
from django.utils import timezone

from .conftest import make_school, make_user

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import messages  # noqa: E402

pytestmark = pytest.mark.django_db
PLACEHOLDER = re.compile(r"%\(\w+\)s")


def test_every_message_has_a_french_translation():
    found = messages.extract()
    french = messages.parse(messages.CATALOGUE)
    missing = [m for m in found if not french.get(m)]
    assert not missing, f"Run scripts/messages.py extract, translate these, then compile: {missing}"
    mismatched = [m for m in found if sorted(PLACEHOLDER.findall(m)) != sorted(PLACEHOLDER.findall(french[m]))]
    assert not mismatched


def test_the_compiled_catalogue_is_up_to_date():
    compiled = messages.CATALOGUE.with_suffix(".mo").read_bytes()
    assert compiled == messages.mo_bytes(messages.parse(messages.CATALOGUE)), "Run scripts/messages.py compile"


def test_errors_follow_the_readers_language(client_for):
    school = make_school("Lycée de Kigali", "Nyarugenge")
    payload = {"username": "newpupil", "password": "Str0ng-pass-123", "role": "student", "grade": "S2"}
    wrong_code = {**payload, "school": school.id, "school_code": "WRONG123"}
    english = client_for().post("/api/auth/register/", wrong_code, format="json")
    assert "doesn't match this school" in str(english.data)
    french = client_for().post("/api/auth/register/", wrong_code, format="json", HTTP_ACCEPT_LANGUAGE="fr")
    assert "ne correspond pas à cette école" in str(french.data)
    # Django's and DRF's own messages come in French too.
    blank = client_for().post("/api/auth/register/", {"role": "student"}, format="json", HTTP_ACCEPT_LANGUAGE="fr")
    assert "Ce champ est obligatoire." in str(blank.data)


def test_billing_emails_use_each_administrators_language(settings):
    from apps.schools import notify

    settings.SUBSCRIPTION_GRACE_DAYS = 3
    school = make_school("APADE", "Kicukiro", paid_until=timezone.now() + timedelta(days=3))
    make_user("adminfr", role="school_admin", school=school, preferred_language="fr")
    make_user("adminen", role="school_admin", school=school, preferred_language="en")
    assert notify.reminder(school, "3_days") == 2
    by_recipient = {m.to[0]: m for m in mail.outbox}
    french, english = by_recipient["adminfr@example.com"], by_recipient["adminen@example.com"]
    assert "se termine dans 3 jour(s)" in french.subject and "payé jusqu'au" in french.body
    month_fr = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    assert month_fr[timezone.localtime(school.paid_until).month - 1] in french.body
    assert "ends in 3 day(s)" in english.subject and "is paid until" in english.body


def test_search_finds_and_shows_french_text(client_for, student, unit, subject):
    from apps.curriculum.models import Lesson, LessonTranslation

    lesson = Lesson.objects.create(unit=unit, slug="linear", title="Linear graphs", body="x", status="published", is_free=True)
    LessonTranslation.objects.create(lesson=lesson, language="fr", title="Fonctions affines", body="Une droite.")
    client = client_for(student)
    french = client.get("/api/search/", {"q": "affines"}, HTTP_ACCEPT_LANGUAGE="fr").data
    assert french["lessons"][0]["title"] == "Fonctions affines"
    assert french["lessons"][0]["subject"] == "Mathématiques"
    assert client.get("/api/search/", {"q": "Mathé"}, HTTP_ACCEPT_LANGUAGE="fr").data["subjects"][0]["name"] == "Mathématiques"
    # English readers keep the English titles and don't search the French text.
    assert client.get("/api/search/", {"q": "affines"}, HTTP_ACCEPT_LANGUAGE="en").data["lessons"] == []


def test_labs_have_french_titles(client_for, student):
    from apps.simulations.models import Simulation

    Simulation.objects.create(
        slug="ohms-law-lab",
        title="Ohm's Law Lab",
        title_fr="Labo de la loi d'Ohm",
        provider="builtin",
        provider_id="ohms",
        description="Change the voltage.",
        description_fr="Changez la tension.",
    )
    client = client_for(student)
    french = client.get("/api/simulations/ohms-law-lab/", HTTP_ACCEPT_LANGUAGE="fr").data
    assert (french["title"], french["description"]) == ("Labo de la loi d'Ohm", "Changez la tension.")
    assert client.get("/api/simulations/ohms-law-lab/", HTTP_ACCEPT_LANGUAGE="en").data["title"] == "Ohm's Law Lab"


def test_quiz_pages_name_the_subject_in_french(client_for, student, quiz_factory):
    quiz = quiz_factory()
    started = client_for(student).post(f"/api/quizzes/{quiz.id}/start/", HTTP_ACCEPT_LANGUAGE="fr").data
    assert started["quiz"]["subject"]["name"] == "Mathématiques"
    listed = client_for(student).get("/api/attempts/", HTTP_ACCEPT_LANGUAGE="fr").data
    rows = listed["results"] if isinstance(listed, dict) else listed
    assert rows[0]["subject"] == "Mathématiques"


def test_the_app_language_wins_over_the_saved_preference(client_for, unit):
    user = make_user("pref", preferred_language="fr")
    client = client_for(user)
    assert client.get("/api/subjects/").data[0]["display_name"] == "Mathématiques"  # no header: the saved preference
    assert client.get("/api/subjects/", HTTP_ACCEPT_LANGUAGE="en").data[0]["display_name"] == "Mathematics"
    assert client.get("/api/subjects/", {"lang": "fr"}, HTTP_ACCEPT_LANGUAGE="en").data[0]["display_name"] == "Mathématiques"
