"""People's text is normalised and stripped of invisible and control characters before it is stored
(apps/core/text.py)."""

import pytest

from apps.accounts.models import User
from apps.assessments.models import Question
from apps.classroom.models import Classroom
from apps.community.models import GroupMembership, Message, SharedNote, StudyGroup
from apps.core.text import MAX_COMBINING, clean_text

pytestmark = pytest.mark.django_db

ZWSP, ZWJ, BOM, RLO, LRI, PDI, SHY = "\u200b", "\u200d", "\ufeff", "\u202e", "\u2066", "\u2069", "\u00ad"
TAG_A = "\U000e0041"  # an invisible "tag" letter


@pytest.mark.parametrize(
    ("raw", "multiline", "expected"),
    [
        ("Cafe\u0301", False, "Caf\u00e9"),  # NFC: e + combining accent becomes one letter
        (f"A{ZWSP}l{ZWJ}i{BOM}n{SHY}e", False, "Aline"),
        (f"Aline{RLO}gnp.exe", False, "Alinegnp.exe"),
        (f"Café {LRI}evil{PDI}", False, "Café evil"),
        ("Aline\x1b[31m red\x07\x7f", False, "Aline[31m red"),
        (f"ignore{TAG_A}{TAG_A} me", False, "ignore me"),
        ("one\ntwo\r\nthree\tfour\u2028five", False, "one two three four five"),
        ("one\ntwo\r\nthree\tfour\u2028five\rsix", True, "one\ntwo\nthree\tfour\nfive\nsix"),
        ("x" + "\u0301" * 50, False, "x" + "\u0301" * MAX_COMBINING),  # "Zalgo" text
        ("Ngưỡng đặc biệt", False, "Ngưỡng đặc biệt"),  # stacked accents of real languages stay
        ("5\u00a0km\u202f; prix\u00a0: 3\u202f€", True, "5\u00a0km\u202f; prix\u00a0: 3\u202f€"),  # no-break spaces stay
        ("Muraho! Ndi umunyeshuri.", False, "Muraho! Ndi umunyeshuri."),
        ("a < b && c > d <script>", True, "a < b && c > d <script>"),  # stored as typed, escaped when shown
        ("lone \ud800 surrogate", False, "lone  surrogate"),
        ("", False, ""),
    ],
)
def test_clean_text(raw, multiline, expected):
    assert clean_text(raw, multiline) == expected


def make_group(user):
    group = StudyGroup.objects.create(name="Physics", created_by=user)
    GroupMembership.objects.create(group=group, user=user, role="owner")
    return group


def test_a_chat_message_of_only_invisible_characters_is_blank(client_for, student):
    group = make_group(student)
    response = client_for(student).post(f"/api/groups/{group.id}/messages/", {"body": ZWSP * 5 + RLO}, format="json")
    assert response.status_code == 400
    assert not Message.objects.exists()


def test_chat_messages_and_notes_are_cleaned(client_for, student):
    group = make_group(student)
    client = client_for(student)
    response = client.post(f"/api/groups/{group.id}/messages/", {"body": f"See{ZWSP} you\r\nat 5{RLO}"}, format="json")
    assert response.status_code == 201, response.data
    assert Message.objects.get().body == "See you\nat 5"
    response = client.post(
        f"/api/groups/{group.id}/notes/",
        {"title": f"Forces{ZWSP}\nand motion", "body": f"# Newton{BOM}\n\n\tF = ma"},
        format="json",
    )
    assert response.status_code == 201, response.data
    note = SharedNote.objects.get()
    assert (note.title, note.body) == ("Forces and motion", "# Newton\n\n\tF = ma")


def test_notes_and_messages_have_length_limits(client_for, student):
    group = make_group(student)
    client = client_for(student)
    assert client.post(f"/api/groups/{group.id}/messages/", {"body": "a" * 2001}, format="json").status_code == 400
    note = {"title": "x", "body": "a" * 20001}
    assert client.post(f"/api/groups/{group.id}/notes/", note, format="json").status_code == 400
    assert client.post("/api/groups/", {"name": "x" * 121}, format="json").status_code == 400


def test_names_shown_to_others_are_cleaned(client_for, student, teacher):
    response = client_for(student).patch(
        "/api/auth/me/", {"first_name": f"Aline{RLO}gnp.exe\x1b[31m", "last_name": f"U{ZWSP}wase"}, format="json"
    )
    assert response.status_code == 200, response.data
    student.refresh_from_db()
    assert (student.first_name, student.last_name) == ("Alinegnp.exe[31m", "Uwase")
    response = client_for(student).post("/api/groups/", {"name": f"Café {LRI}evil{PDI}\nclub"}, format="json")
    assert response.status_code == 201, response.data
    assert StudyGroup.objects.get(pk=response.data["id"]).name == "Café evil club"
    response = client_for(teacher).post("/api/classes/", {"name": f"S1{ZWSP} Maths{RLO}", "grade": "S1"}, format="json")
    assert response.status_code == 201, response.data
    assert Classroom.objects.get().name == "S1 Maths"


def test_questions_written_by_teachers_are_cleaned(client_for, teacher, subject):
    response = client_for(teacher).post(
        "/api/questions/",
        {
            "subject": subject.id,
            "grade": "S2",
            "type": "short",
            "prompt": f"Symbole de l'eau{ZWSP} ?\u2028E\u0301crivez-le.",
            "accepted_answers": ["H2O"],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert Question.objects.get().prompt == "Symbole de l'eau ?\nÉcrivez-le."


def test_long_text_has_a_ceiling(client_for, teacher, unit, settings):
    settings.TEXT_MAX_CHARS = 1000  # read when the serializer fields are built
    payload = {"unit": unit.id, "slug": "long", "title": "Long", "body": "x" * 1001}
    response = client_for(teacher).post("/api/lessons/", payload, format="json")
    assert response.status_code == 400 and "body" in response.data


def test_lone_surrogates_are_refused_not_a_server_error(client_for, student):
    group = make_group(student)
    for body in (b'{"body": "hi \\ud800 there"}', b'{"body": "ok", "\\udfff": 1}'):
        response = client_for(student).post(f"/api/groups/{group.id}/messages/", data=body, content_type="application/json")
        assert response.status_code == 400
    response = client_for().post(
        "/api/auth/login/", data=b'{"identifier": "x", "password": "\\ud83d"}', content_type="application/json"
    )
    assert response.status_code == 400


def test_roster_imports_are_cleaned(client_for, teacher):
    classroom = Classroom.objects.create(name="S1", grade="S1", teacher=teacher)
    csv = f"first_name,last_name\nAline{ZWSP},Uwase{RLO}\n{ZWSP}{BOM},Nobody\nJean\x1b[2J,Mugabo\n"
    response = client_for(teacher).post(f"/api/classes/{classroom.id}/import_roster/", {"csv": csv}, format="json")
    assert response.status_code == 200
    rows = response.data["rows"]
    assert (rows[0]["first_name"], rows[0]["last_name"]) == ("Aline", "Uwase")
    assert rows[1]["errors"]  # a name of invisible characters only is missing
    assert rows[2]["first_name"] == "Jean[2J"


def test_saving_from_the_admin_or_code_cleans_too(student, teacher):
    # The Django admin, roster imports and scripts save through the models: the same cleaning applies.
    group = make_group(student)
    message = Message.objects.create(group=group, author=student, body=f"hi{ZWSP}{RLO}\r\nthere")
    message.refresh_from_db()
    assert message.body == "hi\nthere"
    classroom = Classroom.objects.create(name=f" S1{BOM}\tMaths ", grade="S1", teacher=teacher)
    classroom.refresh_from_db()
    assert classroom.name == "S1 Maths"
    student.first_name = f"Ali{ZWSP}ne\n"
    student.save(update_fields=["first_name"])
    student.refresh_from_db()
    assert student.first_name == "Aline"


def test_passwords_and_student_code_are_never_changed(client_for):
    password = f"Str0ng{ZWSP}-pass-é-123"
    response = client_for().post(
        "/api/auth/register/", {"username": "newkid", "password": password, "first_name": "New", "grade": "S2"}, format="json"
    )
    assert response.status_code == 201, response.data
    assert User.objects.get(username="newkid").check_password(password)
    assert not User.objects.get(username="newkid").check_password(password.replace(ZWSP, ""))


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "JAVASCRIPT:alert(1)", "data:text/html,<script>alert(1)</script>", "vbscript:x", "//evil.example/x"],
)
def test_links_people_give_must_be_web_addresses(client_for, teacher, subject, unit, url):
    # Shown as links to other people (resources, lesson videos): only http(s) and ftp addresses are taken.
    client = client_for(teacher)
    resource = {"subject": subject.id, "kind": "notes", "title": "Notes", "url": url}
    assert client.post("/api/resources/", resource, format="json").status_code == 400
    lesson = {"unit": unit.id, "slug": "video", "title": "Video", "body": "x", "video_url": url}
    assert client.post("/api/lessons/", lesson, format="json").status_code == 400


def test_short_answers_match_however_the_accent_was_typed(student, subject, quiz_factory):
    # Student answers are stored as NFC; an accepted answer typed as e + accent (or saved before answers
    # were cleaned, or with an invisible character pasted in) must still match them.
    from apps.assessments import services
    from apps.assessments.models import Answer, Attempt

    attempt = Attempt.objects.create(user=student, quiz=quiz_factory())
    question = Question.objects.create(
        subject=subject, grade="S2", type=Question.Type.SHORT, prompt="?", accepted_answers=["Café", f"H{ZWSP}2O"]
    )
    for typed in ("café", "h2o"):
        answer = Answer.objects.create(attempt=attempt, question=question, text_answer=typed)
        assert services.score_answer(answer)[0] is True, typed
        answer.delete()


def test_accepted_answers_are_cleaned(client_for, teacher, subject):
    payload = {
        "subject": subject.id,
        "grade": "S2",
        "type": "short",
        "prompt": "Boisson ?",
        "accepted_answers": ["Café", f"{ZWSP}{BOM}", f"th{RLO}é\n"],
    }
    response = client_for(teacher).post("/api/questions/", payload, format="json")
    assert response.status_code == 201, response.data
    assert Question.objects.get().accepted_answers == ["Café", "thé"]


def test_santa_history_is_cleaned(student):
    from apps.tutor.services import clean_history

    history = [{"role": "user", "content": f"Hi{TAG_A}{TAG_A}{ZWSP}"}, {"role": "assistant", "content": f"Muraho{RLO}!"}]
    turns, dropped = clean_history(history)
    assert turns == [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Muraho!"}] and dropped == 0


def test_every_cleaned_field_is_a_text_field():
    from django.apps import apps
    from django.db import models

    from apps.core.text import CLEANED_FIELDS

    for label, names in CLEANED_FIELDS.items():
        for name in names:
            field = apps.get_model(label)._meta.get_field(name)
            assert isinstance(field, models.CharField | models.TextField), (label, name)


def test_an_invisible_character_does_not_make_a_bank_reference_new(client_for):
    # Recorded bank transfers are unique by reference: "BK<zero-width space>4471" is the transfer "BK4471".
    from apps.schools.models import Payment

    from .conftest import make_school, make_user

    lycee = make_school("Lycee de Kigali", "Nyarugenge")
    client = client_for(make_user("staff", role="admin"))
    url = f"/api/admin/schools/{lycee.id}/payments/"
    body = {"months": 1, "amount": "200", "currency": "USD", "note": f"Bank{ZWSP} of Kigali{RLO}", "external_reference": "BK4471"}
    assert client.post(url, body, format="json").status_code == 201
    again = client.post(url, {**body, "external_reference": f"BK{ZWSP}44{SHY}71"}, format="json")
    assert again.status_code == 400 and "external_reference" in again.data
    assert Payment.objects.get().note == "Bank of Kigali"
