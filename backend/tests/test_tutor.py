from types import SimpleNamespace

import anthropic
import pytest

from apps.curriculum.models import Lesson
from apps.tutor import services
from apps.tutor.models import TutorExchange

from .conftest import add_mcq, make_quiz

pytestmark = pytest.mark.django_db


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.calls = []
        self.response = response
        self.error = error

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def fake_response(text="Here is a hint.", stop_reason="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        model="claude-opus-5-5",
        usage=SimpleNamespace(input_tokens=120, output_tokens=40),
    )


@pytest.fixture
def tutor(settings, monkeypatch):
    settings.TUTOR_ENABLED = True
    messages = FakeMessages(fake_response())
    monkeypatch.setattr(services, "get_client", lambda: SimpleNamespace(beta=SimpleNamespace(messages=messages)))
    return messages


def system_text(call):
    return "\n".join(block["text"] for block in call["system"])


def test_status_and_disabled(client_for, student, settings):
    settings.TUTOR_ENABLED = False
    client = client_for(student)
    assert client.get("/api/tutor/status/").data == {"enabled": False, "reason": ""}
    assert client.post("/api/tutor/ask/", {"message": "hi"}, format="json").status_code == 503


def test_lesson_question_uses_lesson_and_fallbacks(client_for, student, lesson, tutor):
    response = client_for(student).post("/api/tutor/ask/", {"message": "Explain gradient", "lesson": lesson.slug}, format="json")
    assert response.status_code == 200
    assert response.data["reply"] == "Here is a hint."
    call = tutor.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in call["betas"]
    assert lesson.body in system_text(call)
    assert call["messages"][-1] == {"role": "user", "content": "Explain gradient"}
    exchange = TutorExchange.objects.get()
    assert exchange.lesson == lesson and exchange.output_tokens == 40


def test_draft_lesson_is_not_shared_with_tutor(client_for, student, unit, tutor):
    Lesson.objects.create(unit=unit, slug="draft", title="Draft", body="secret", status="draft")
    response = client_for(student).post("/api/tutor/ask/", {"message": "?", "lesson": "draft"}, format="json")
    assert response.status_code == 404
    assert tutor.calls == []


def _start(client, quiz):
    return client.post(f"/api/quizzes/{quiz.id}/start/").data


def test_tutor_off_during_exams(client_for, student, subject, unit, tutor):
    quiz = make_quiz(subject, unit, [add_mcq(subject, unit)], feedback_mode="after_submit")
    client = client_for(student)
    attempt = _start(client, quiz)
    response = client.post(
        "/api/tutor/ask/",
        {"message": "answer?", "attempt": attempt["id"], "question": attempt["questions"][0]["id"]},
        format="json",
    )
    assert response.status_code == 403
    assert tutor.calls == []


def test_practice_question_in_progress_never_shares_the_answer(client_for, student, subject, unit, tutor):
    question = add_mcq(subject, unit, "What is 7 x 8?", "fifty-six", ("forty-eight", "sixty-four"))
    question.explanation = "SECRET-EXPLANATION"
    question.save()
    quiz = make_quiz(subject, unit, [question], feedback_mode="immediate")
    client = client_for(student)
    attempt = _start(client, quiz)
    response = client.post(
        "/api/tutor/ask/", {"message": "hint please", "attempt": attempt["id"], "question": question.id}, format="json"
    )
    assert response.status_code == 200
    context = system_text(tutor.calls[0])
    assert "STILL ANSWERING" in context
    assert "SECRET-EXPLANATION" not in context
    assert "Correct option" not in context


def test_after_submitting_the_tutor_sees_the_solution(client_for, student, subject, unit, tutor):
    question = add_mcq(subject, unit, "What is 7 x 8?", "fifty-six", ("forty-eight", "sixty-four"))
    quiz = make_quiz(subject, unit, [question], feedback_mode="after_submit")
    client = client_for(student)
    attempt = _start(client, quiz)
    wrong = question.choices.get(text="forty-eight").id
    client.post(f"/api/attempts/{attempt['id']}/answer/", {"question": question.id, "choice_ids": [wrong]}, format="json")
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    response = client.post(
        "/api/tutor/ask/", {"message": "why?", "attempt": attempt["id"], "question": question.id}, format="json"
    )
    assert response.status_code == 200
    context = system_text(tutor.calls[0])
    assert "Correct option(s): fifty-six" in context
    assert "Student's answer: forty-eight" in context


def test_cannot_ask_about_someone_elses_attempt(client_for, student, other_student, quiz_factory, tutor):
    attempt = _start(client_for(student), quiz_factory(feedback_mode="immediate"))
    response = client_for(other_student).post("/api/tutor/ask/", {"message": "?", "attempt": attempt["id"]}, format="json")
    assert response.status_code == 404


def test_refusal_gets_a_friendly_reply(client_for, student, tutor):
    tutor.response = fake_response(text="", stop_reason="refusal")
    response = client_for(student).post("/api/tutor/ask/", {"message": "something off-topic"}, format="json")
    assert response.status_code == 200
    assert response.data["reply"] == services.REFUSAL_REPLY


def test_history_must_alternate(client_for, student, tutor):
    bad = [{"role": "assistant", "content": "hi"}, {"role": "assistant", "content": "again"}]
    response = client_for(student).post("/api/tutor/ask/", {"message": "?", "history": bad}, format="json")
    assert response.status_code == 400
    good = [{"role": "user", "content": "What is a cell?"}, {"role": "assistant", "content": "The unit of life."}]
    response = client_for(student).post("/api/tutor/ask/", {"message": "More?", "history": good}, format="json")
    assert response.status_code == 200
    assert [m["role"] for m in tutor.calls[-1]["messages"]] == ["user", "assistant", "user"]


def test_rate_limited_api_returns_503(client_for, student, tutor):
    import httpx2

    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    tutor.error = anthropic.RateLimitError("slow down", response=httpx2.Response(429, request=request), body=None)
    response = client_for(student).post("/api/tutor/ask/", {"message": "?"}, format="json")
    assert response.status_code == 503
    assert not TutorExchange.objects.exists()


def test_replies_in_the_students_language(client_for, student, tutor):
    student.preferred_language = "fr"
    student.save()
    client_for(student).post("/api/tutor/ask/", {"message": "Seli ni nini?"}, format="json")
    assert "Reply in French" in system_text(tutor.calls[0])


def test_tutor_follows_the_reading_language(client_for, student, lesson, tutor):
    from apps.curriculum.models import LessonTranslation

    LessonTranslation.objects.create(lesson=lesson, language="fr", title="Graphiques", body="CORPS EN FRANÇAIS")
    response = client_for(student).post(
        "/api/tutor/ask/", {"message": "Explique", "lesson": lesson.slug, "lang": "fr"}, format="json"
    )
    assert response.status_code == 200
    context = system_text(tutor.calls[0])
    assert "Reply in French" in context and "CORPS EN FRANÇAIS" in context and "# Hello" not in context

    tutor.response = fake_response(text="", stop_reason="refusal")
    refused = client_for(student).post("/api/tutor/ask/", {"message": "hors sujet", "lang": "fr"}, format="json")
    assert refused.data["reply"] == services.REFUSAL_REPLIES["fr"]
