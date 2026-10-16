"""Santa's allowances (apps/tutor/usage.py): per-student daily and monthly questions and tokens, a per-school daily
budget, the most one request may send and write, and what the student and platform admins are shown. The model is
the fake server of test_tutor.py, which reports 120 prompt and 40 completion tokens for each request."""

from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.tutor import services, usage
from apps.tutor.models import SantaUsage, TutorExchange

from .conftest import make_school, make_user
from .test_tutor import ask, biology, santa, stream  # noqa: F401 - fixtures

pytestmark = pytest.mark.django_db

TOKENS = 160  # what the fake model server reports for one request


@pytest.fixture
def limits(settings):
    settings.SANTA_USER_DAILY_QUESTIONS = 3
    settings.SANTA_USER_MONTHLY_QUESTIONS = 50
    settings.SANTA_USER_DAILY_TOKENS = 0
    settings.SANTA_USER_MONTHLY_TOKENS = 0
    settings.SANTA_SCHOOL_DAILY_TOKENS = 0
    return settings


def used(user, days_ago=0, **counts):
    """Pretend the student already used Santa that day."""
    day = usage._today() - timedelta(days=days_ago)
    return SantaUsage.objects.create(user=user, school=user.school, day=day, **counts)


# --- Counting --------------------------------------------------------------------------------------


def test_each_model_answer_is_counted_with_its_tokens(client_for, student, santa, limits):  # noqa: F811
    client = client_for(student)
    ask(client, message="What is a cell?")
    santa.script = [{"content": "", "tool_calls": [("calculate", {"expression": "2+2"})]}, {"content": "4"}]
    ask(client, message="2+2?")
    row = SantaUsage.objects.get(user=student)
    assert row.day == timezone.localdate() and row.school == student.school
    # The second question took two requests (the calculator round and the answer).
    assert (row.questions, row.input_tokens, row.output_tokens, row.limited) == (2, 360, 120, 0)


def test_answers_from_the_lessons_are_free(client_for, student, biology, settings, limits):  # noqa: F811
    settings.SANTA_URL = ""  # no model: Santa answers with lesson passages
    for _ in range(5):
        response = ask(client_for(student), message="What does the cell membrane do?")
        assert response.data["fallback"] == "not_installed"
    assert not SantaUsage.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_stopping_an_answer_early_does_not_make_it_free(client_for, student, santa, limits):  # noqa: F811
    santa.script = [{"content": "A long answer that the student stops before the server says how many tokens it used."}]
    response = client_for(student).post("/api/tutor/stream/", {"message": "Explain"}, format="json")
    content = iter(response.streaming_content)
    next(content)
    next(content)
    response.close()
    row = SantaUsage.objects.get(user=student)
    assert row.questions == 1
    # No usage arrived from the server, so the tokens are estimated from what was sent (the system prompt alone
    # is over 1,000 characters).
    assert row.input_tokens >= len(services.SYSTEM_PROMPT) // usage.CHARS_PER_TOKEN


# --- Per-student limits ------------------------------------------------------------------------------


def test_the_daily_question_limit_answers_from_the_lessons(client_for, student, biology, santa, limits):  # noqa: F811
    client = client_for(student)
    for left in (2, 1, 0):
        response = ask(client, message="What does the cell membrane do?")
        assert response.data["fallback"] is None and response.data["allowance"]["questions_left_today"] == left
    calls = len(santa.calls)
    response = ask(client, message="What does the cell membrane do?")
    assert response.status_code == 200 and len(santa.calls) == calls  # the model was not asked
    assert response.data["fallback"] == usage.DAY
    reply = response.data["reply"]
    assert "used today's questions for Santa's AI" in reply and "again tomorrow" in reply
    assert "Here is what your lessons say" in reply and "cell membrane controls" in reply  # still helped
    assert response.data["sources"][0]["slug"] == "the-cell"
    assert response.data["allowance"]["reached"] == usage.DAY
    assert SantaUsage.objects.get(user=student).limited == 1
    assert TutorExchange.objects.filter(stop_reason="fallback:limit_day").count() == 1


def test_the_limit_is_said_in_french(client_for, student, biology, santa, limits):  # noqa: F811
    used(student, questions=3)
    events, _ = stream(client_for(student), message="La membrane ?", lang="fr")
    done = events[-1]
    assert done["fallback"] == usage.DAY
    assert "Vous avez utilisé les questions d'aujourd'hui" in done["reply"] and "demain" in done["reply"]
    assert "Voici ce que disent vos leçons" in done["reply"]


def test_a_new_day_brings_new_questions(client_for, student, santa, limits):  # noqa: F811
    used(student, days_ago=1, questions=3)
    response = ask(client_for(student), message="Hello")
    assert response.data["fallback"] is None and response.data["allowance"]["questions_left_today"] == 2


def test_the_monthly_question_limit(client_for, student, santa, limits, monkeypatch):  # noqa: F811
    limits.SANTA_USER_MONTHLY_QUESTIONS = 4
    monkeypatch.setattr(usage, "_today", lambda: date(2026, 10, 16))
    used(student, days_ago=16, questions=40)  # 30 September: last month doesn't count
    used(student, days_ago=6, questions=3)
    client = client_for(student)
    assert ask(client, message="Hello").data["allowance"]["questions_left_month"] == 0
    response = ask(client, message="Hello again")
    assert response.data["fallback"] == usage.MONTH and "again next month" in response.data["reply"]
    assert response.data["allowance"]["questions_left_today"] == 2  # today's questions aren't the problem


def test_the_daily_and_monthly_token_limits(client_for, student, santa, limits):  # noqa: F811
    limits.SANTA_USER_DAILY_QUESTIONS = 0
    limits.SANTA_USER_DAILY_TOKENS = 2 * TOKENS
    client = client_for(student)
    first = ask(client, message="One")
    assert first.data["allowance"]["time_left_percent"] == 50
    ask(client, message="Two")
    response = ask(client, message="Three")
    assert response.data["fallback"] == usage.DAY and response.data["allowance"]["time_left_percent"] == 0
    limits.SANTA_USER_DAILY_TOKENS = 0
    limits.SANTA_USER_MONTHLY_TOKENS = 2 * TOKENS
    assert ask(client, message="Four").data["fallback"] == usage.MONTH


# --- The school's daily budget ------------------------------------------------------------------------


def test_a_schools_daily_budget_is_shared_by_its_members(client_for, student, other_student, santa, limits):  # noqa: F811
    limits.SANTA_SCHOOL_DAILY_TOKENS = 2 * TOKENS
    elsewhere = make_user("elsewhere", school=make_school("Lycee", paid_until=timezone.now() + timedelta(days=30)))
    ask(client_for(student), message="One")
    ask(client_for(other_student), message="Two")  # the same school
    response = ask(client_for(other_student), message="Three")
    assert response.data["fallback"] == usage.SCHOOL
    assert "Your school has used today's time with Santa's AI" in response.data["reply"]
    assert ask(client_for(student), message="Four").data["fallback"] == usage.SCHOOL
    assert ask(client_for(elsewhere), message="Five").data["fallback"] is None  # another school's budget


def test_a_platform_admin_without_a_school_has_no_school_budget(client_for, admin_user, santa, limits):  # noqa: F811
    limits.SANTA_SCHOOL_DAILY_TOKENS = 1
    assert ask(client_for(admin_user), message="Hi").data["fallback"] is None
    assert ask(client_for(admin_user), message="Again").data["fallback"] is None


# --- What the student sees -----------------------------------------------------------------------------


def test_the_student_sees_what_is_left(client_for, student, santa, limits):  # noqa: F811
    client = client_for(student)
    assert client.get("/api/tutor/status/").data["allowance"] == {
        "questions_left_today": 3,
        "questions_per_day": 3,
        "questions_left_month": 50,
        "questions_per_month": 50,
        "time_left_percent": None,
        "reached": "",
    }
    events, _ = stream(client, message="Hi")
    assert events[-1]["allowance"]["questions_left_today"] == 2
    assert client.get("/api/tutor/status/").data["allowance"]["questions_left_today"] == 2


def test_no_limit_means_none_left_to_count(client_for, student, santa, settings):  # noqa: F811
    for name in ("DAILY_QUESTIONS", "MONTHLY_QUESTIONS", "DAILY_TOKENS", "MONTHLY_TOKENS"):
        setattr(settings, f"SANTA_USER_{name}", 0)
    settings.SANTA_SCHOOL_DAILY_TOKENS = 0
    used(student, questions=10_000, input_tokens=10**9)
    response = ask(client_for(student), message="Hi")
    assert response.data["fallback"] is None
    assert response.data["allowance"] == {
        "questions_left_today": None,
        "questions_per_day": None,
        "questions_left_month": None,
        "questions_per_month": None,
        "time_left_percent": None,
        "reached": "",
    }


def test_users_without_santa_get_no_allowance(client_for, settings, santa):  # noqa: F811
    outsider = make_user("outsider", school=None)
    data = client_for(outsider).get("/api/tutor/status/").data
    assert data["enabled"] is False and data["allowance"] is None


# --- One request ------------------------------------------------------------------------------------


def test_max_tokens_is_for_the_whole_answer(client_for, student, santa, settings, limits):  # noqa: F811
    settings.SANTA_MAX_TOKENS = 100  # the fake server reports 40 completion tokens per request
    santa.script = [
        {"content": "", "tool_calls": [("calculate", {"expression": "1+1"})]},
        {"content": "", "tool_calls": [("calculate", {"expression": "2+2"})]},
        {"content": "", "tool_calls": [("calculate", {"expression": "3+3"})]},
        {"content": "never asked"},
    ]
    response = ask(client_for(student), message="Add")
    assert [call["body"]["max_tokens"] for call in santa.calls] == [100, 60, 20]
    assert "never asked" not in response.data["reply"]
    assert "ran out of space" in response.data["reply"]


def test_max_input_tokens_cuts_what_is_sent(client_for, student, unit, santa, settings, limits):  # noqa: F811
    from apps.curriculum.models import Lesson

    paragraph = "Photosynthesis makes glucose from carbon dioxide and water using light. " * 30
    for i in range(6):
        Lesson.objects.create(unit=unit, slug=f"p{i}", title=f"Plants {i}", status="published", body=f"## P{i}\n\n{paragraph}")
    sizes = {}
    for tokens in (2800, 600):
        settings.SANTA_MAX_INPUT_TOKENS = tokens
        ask(client_for(student), message="photosynthesis glucose")
        sizes[tokens] = len(santa.calls[-1]["body"]["messages"][-1]["content"])
        assert sizes[tokens] <= services.turn_chars() + 1000  # labels, the reminder
    assert sizes[600] < sizes[2800]


def test_parallel_answers_are_capped(client_for, student, other_student, biology, santa, settings, limits):  # noqa: F811
    settings.SANTA_PARALLEL = 2
    cache.add("santa:slot:0", "someone", 60)
    assert ask(client_for(student), message="cell membrane").data["fallback"] is None  # slot 1 was free
    cache.add("santa:slot:1", "someone else", 60)
    response = ask(client_for(other_student), message="cell membrane")
    assert response.data["fallback"] == "busy" and len(santa.calls) == 1
    assert not SantaUsage.objects.filter(user=other_student).exists()  # a busy answer from the lessons is free


# --- Platform admins ---------------------------------------------------------------------------------


def test_platform_admins_see_the_usage(client_for, student, other_student, admin_user, santa, limits):  # noqa: F811
    ask(client_for(student), message="One")
    ask(client_for(student), message="Two")
    ask(client_for(other_student), message="Three")
    used(make_user("old"), days_ago=40, questions=7)
    data = client_for(admin_user).get("/api/admin/stats/").data["santa"]
    assert data["today"] == {"questions": 3, "input_tokens": 360, "output_tokens": 120, "limited": 0, "students": 2}
    assert data["last_30_days"]["questions"] == 3
    assert data["top_schools_today"] == [{"school": student.school.name, "questions": 3, "tokens": 480, "students": 2}]
    assert data["limits"]["user_daily_questions"] == 3 and data["limits"]["max_output_tokens"] == 600
    assert client_for(student).get("/api/admin/stats/").status_code == 403
