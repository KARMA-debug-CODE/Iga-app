"""Santa, Iga's learning assistant. Its model runs on llama.cpp's server; here a small fake server speaks the same
OpenAI-compatible API over real HTTP (plain and streamed answers, tool calls, loading, errors), so these tests
cover Django's side: what Santa may see, the calculator, lesson passages, fallbacks and the exam lock."""

import builtins
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.core.cache import cache

from apps.curriculum.models import Lesson, LessonTranslation, Subject, Unit
from apps.tutor import calculator, llm, retrieval, services
from apps.tutor.models import TutorExchange

from .conftest import add_mcq, make_quiz, make_school, make_user

pytestmark = pytest.mark.django_db

KEY = "s3cret"
LOADING = {"error": {"code": 503, "message": "Loading model", "type": "unavailable_error"}}


class FakeSanta(BaseHTTPRequestHandler):
    """llama-server's /health and /v1/chat/completions, answering from a script of replies."""

    calls = []
    script = []
    loading = False
    reject_tools = False
    garbage = False
    delay = 0
    cut_after = None  # stream: drop the connection after this many pieces of text
    too_long = 0  # refuse this many requests, as llama-server does when a request doesn't fit a slot
    shape = None  # valid JSON that isn't an answer: sent as the reply, or as a streamed chunk

    def log_message(self, *args):
        pass

    def _json(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            return self._json(503, LOADING) if FakeSanta.loading else self._json(200, {"status": "ok"})
        return self._json(404, {"error": {"message": "not found"}})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeSanta.calls.append({"path": self.path, "body": body, "auth": self.headers.get("Authorization")})
        if FakeSanta.loading:
            return self._json(503, LOADING)
        if self.headers.get("Authorization") != f"Bearer {KEY}":
            return self._json(401, {"error": {"code": 401, "message": "Invalid API Key"}})
        if FakeSanta.too_long:
            FakeSanta.too_long -= 1
            message = "request (5120 tokens) exceeds the available context size (4096 tokens), try increasing it"
            return self._json(400, {"error": {"code": 400, "message": message, "type": "exceed_context_size_error"}})
        if FakeSanta.reject_tools and body.get("tools"):
            return self._json(400, {"error": {"code": 400, "message": "tools param requires --jinja flag"}})
        if FakeSanta.shape is not None and not body.get("stream"):
            return self._json(200, FakeSanta.shape)
        if FakeSanta.delay:
            time.sleep(FakeSanta.delay)
        if FakeSanta.garbage:
            data = b"<html>gateway error</html>"
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        step = FakeSanta.script.pop(0) if FakeSanta.script else {"content": "Here is a hint."}
        content, calls = step.get("content", ""), step.get("tool_calls", [])
        finish = step.get("finish_reason") or ("tool_calls" if calls else "stop")
        usage = {"prompt_tokens": 120, "completion_tokens": 40, "total_tokens": 160}
        tool_calls = [
            {"id": f"call_{i}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}
            for i, (name, args) in enumerate(calls)
        ]
        if not body.get("stream"):
            message = {"role": "assistant", "content": content or None}
            if tool_calls:
                message["tool_calls"] = tool_calls
            return self._json(
                200,
                {
                    "object": "chat.completion",
                    "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                    "usage": usage,
                },
            )
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        def send(chunk):
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.flush()

        def delta(d, finish_reason=None):
            send({"object": "chat.completion.chunk", "choices": [{"index": 0, "delta": d, "finish_reason": finish_reason}]})

        delta({"role": "assistant", "content": None})
        self.wfile.write(b": keep-alive\n\n")
        if FakeSanta.shape is not None:
            return send(FakeSanta.shape)
        pieces = [content[i : i + 4] for i in range(0, len(content), 4)]
        for n, piece in enumerate(pieces):
            if FakeSanta.cut_after is not None and n >= FakeSanta.cut_after:
                return  # the connection drops half-way
            delta({"content": piece})
        for i, call in enumerate(tool_calls):
            # Tool calls arrive in pieces: the name first, then the arguments in two parts.
            arguments = call["function"]["arguments"]
            delta(
                {
                    "tool_calls": [
                        {
                            "index": i,
                            "id": call["id"],
                            "type": "function",
                            "function": {"name": call["function"]["name"], "arguments": ""},
                        }
                    ]
                }
            )
            delta({"tool_calls": [{"index": i, "function": {"arguments": arguments[:5]}}]})
            delta({"tool_calls": [{"index": i, "function": {"arguments": arguments[5:]}}]})
        delta({}, finish)
        send({"object": "chat.completion.chunk", "choices": [], "usage": usage})
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.write(b'data: {"choices": [{"delta": {"content": "AFTER THE END"}}]}\n\n')


@pytest.fixture
def santa(settings):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeSanta)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    FakeSanta.calls, FakeSanta.script = [], []
    FakeSanta.loading = FakeSanta.reject_tools = FakeSanta.garbage = False
    FakeSanta.delay, FakeSanta.cut_after = 0, None
    FakeSanta.too_long, FakeSanta.shape = 0, None
    settings.SANTA_URL = f"http://127.0.0.1:{server.server_address[1]}"
    settings.SANTA_API_KEY = KEY
    settings.SANTA_MODEL_NAME = "santa"
    settings.SANTA_TIMEOUT_SECONDS = 20
    yield FakeSanta
    server.shutdown()
    server.server_close()


@pytest.fixture
def gradient_lesson(unit):
    return Lesson.objects.create(
        unit=unit,
        slug="linear",
        title="Linear graphs",
        status="published",
        body=(
            "## Gradient\n\nThe gradient is rise over run: $m = \\frac{y_2 - y_1}{x_2 - x_1}$.\n\n"
            "## The y-intercept\n\nThe line crosses the y-axis at $c$."
        ),
    )


@pytest.fixture
def biology(db):
    subject = Subject.objects.create(code="biology", name="Biology", name_fr="Biologie")
    unit = Unit.objects.create(subject=subject, grade="S1", number=1, title="Cells")
    lesson = Lesson.objects.create(
        unit=unit,
        slug="the-cell",
        title="The cell",
        status="published",
        body="## Parts of a cell\n\nThe cell membrane controls what enters and leaves the cell. The nucleus holds DNA.",
    )
    LessonTranslation.objects.create(
        lesson=lesson,
        language="fr",
        title="La cellule",
        body="## Les parties d'une cellule\n\nLa membrane cellulaire contrôle ce qui entre et sort de la cellule.",
    )
    return lesson


def ask(client, **body):
    return client.post("/api/tutor/ask/", {"message": "?", **body}, format="json")


def stream(client, **body):
    """The events of a streamed answer, and the response."""
    response = client.post("/api/tutor/stream/", {"message": "?", **body}, format="json")
    if response.status_code != 200:
        return [], response
    raw = b"".join(response.streaming_content).decode()
    events = [json.loads(block[6:]) for block in raw.split("\n\n") if block.startswith("data: ")]
    response.raw_text = raw
    return events, response


def last_prompt(santa):
    """The student's turn in the last request to the model."""
    return santa.calls[-1]["body"]["messages"][-1]["content"]


def said(user, *replies):
    """Log answers as Santa's, so the browser may send them back as earlier turns."""
    for reply in replies:
        TutorExchange.objects.create(user=user, message="earlier", reply=reply, model="santa", stop_reason="stop")


# --- Status ---------------------------------------------------------------------------------


def test_status_reports_each_state(client_for, student, santa, settings):
    client = client_for(student)
    assert client.get("/api/tutor/status/").data == {"enabled": True, "reason": "", "state": "ready", "exam": None}

    cache.clear()
    santa.loading = True
    assert client.get("/api/tutor/status/").data["state"] == "loading"

    cache.clear()
    settings.SANTA_URL = "http://127.0.0.1:9"  # nothing listens there
    assert client.get("/api/tutor/status/").data["state"] == "unavailable"

    settings.SANTA_URL = ""
    assert client.get("/api/tutor/status/").data == {"enabled": True, "reason": "", "state": "not_installed", "exam": None}


def test_status_says_when_an_exam_switches_santa_off(client_for, student, subject, unit, santa):
    quiz = make_quiz(subject, unit, [add_mcq(subject, unit)], feedback_mode="after_submit", title="Class test")
    client = client_for(student)
    attempt = client.post(f"/api/quizzes/{quiz.id}/start/").data
    data = client.get("/api/tutor/status/").data
    assert data["state"] == "exam" and data["exam"] == {"attempt": attempt["id"], "quiz": "Class test"}


# --- Answers from the model -------------------------------------------------------------------


def test_plain_answer_from_a_lesson(client_for, student, gradient_lesson, santa):
    santa.script = [{"content": "The **gradient** tells you how steep the line is."}]
    response = ask(client_for(student), message="What is the gradient?", lesson=gradient_lesson.slug)
    assert response.status_code == 200
    assert response.data["reply"] == "The **gradient** tells you how steep the line is."
    assert response.data["fallback"] is None
    assert response.data["sources"][0]["url"] == "/lessons/linear"
    assert response.data["sources"][0]["title"] == "Linear graphs"

    call = santa.calls[0]
    assert call["path"] == "/v1/chat/completions" and call["auth"] == f"Bearer {KEY}"
    body = call["body"]
    assert body["model"] == "santa" and body["stream"] is False
    assert body["max_tokens"] == 600 and body["temperature"] == 0.6
    assert body["tools"][0]["function"]["name"] == "calculate"
    system, turn = body["messages"][0], body["messages"][-1]
    assert system == {"role": "system", "content": services.SYSTEM_PROMPT}
    assert "Santa, Iga's learning assistant" in system["content"]
    # Everything about this request is in the student's turn; the system prompt stays the same for the cache.
    assert "rise over run" in turn["content"] and "Reply in English" in turn["content"]
    assert "<student_message>\nWhat is the gradient?\n</student_message>" in turn["content"]
    assert turn["content"].endswith(services.REMINDER)  # the app has the last word, not the student

    exchange = TutorExchange.objects.get()
    assert exchange.lesson == gradient_lesson and exchange.model == "santa"
    assert exchange.stop_reason == "stop" and exchange.input_tokens == 120 and exchange.output_tokens == 40


def test_the_system_prompt_is_the_same_for_every_request(client_for, student, gradient_lesson, subject, santa):
    client = client_for(student)
    ask(client, message="What is the gradient?", lesson=gradient_lesson.slug)
    ask(client, message="Bonjour", subject=subject.code, lang="fr")
    first, second = (c["body"]["messages"][0] for c in santa.calls)
    assert first == second


def test_streamed_answer(client_for, student, gradient_lesson, santa):
    santa.script = [{"content": "Rise over run: $m = 2$."}]
    events, response = stream(client_for(student), message="gradient please", lesson=gradient_lesson.slug)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/event-stream")
    assert response["X-Accel-Buffering"] == "no"
    assert santa.calls[0]["body"]["stream"] is True
    assert events[0] == {"type": "start"}
    deltas = [e["text"] for e in events if e["type"] == "delta"]
    assert len(deltas) > 1 and "".join(deltas) == "Rise over run: $m = 2$."
    assert "AFTER THE END" not in response.raw_text  # nothing after data: [DONE]
    assert ": ping" in response.raw_text  # keep-alive lines are passed on
    done = events[-1]
    assert done["type"] == "done" and done["reply"] == "Rise over run: $m = 2$."
    assert done["sources"][0]["slug"] == "linear" and done["fallback"] is None
    assert TutorExchange.objects.get().reply == "Rise over run: $m = 2$."


@pytest.mark.parametrize("streamed", [False, True])
def test_the_model_uses_the_calculator(client_for, student, santa, streamed):
    santa.script = [
        {"content": "", "tool_calls": [("calculate", {"expression": "1250 * 12"})]},
        {"content": "You pay **15000 FRW** in a year."},
    ]
    client = client_for(student)
    if streamed:
        events, _ = stream(client, message="1250 FRW a month for a year?")
        done = events[-1]
        assert {"type": "tool", "name": "calculate", "expression": "1250 * 12", "result": "15000"} in events
    else:
        done = ask(client, message="1250 FRW a month for a year?").data
    assert done["reply"] == "You pay **15000 FRW** in a year."
    assert done["tools"] == [{"expression": "1250 * 12", "result": "15000"}]
    assert len(santa.calls) == 2
    follow_up = santa.calls[1]["body"]["messages"]
    assert follow_up[-2]["role"] == "assistant" and follow_up[-2]["tool_calls"][0]["function"]["name"] == "calculate"
    assert follow_up[-1] == {"role": "tool", "tool_call_id": "call_0", "name": "calculate", "content": "15000"}


def test_tool_rounds_are_limited(client_for, student, santa):
    again = {"content": "", "tool_calls": [("calculate", {"expression": "2 + 2"})]}
    santa.script = [again, again, again, {"content": "It is 4."}]
    response = ask(client_for(student), message="2 + 2?")
    assert response.data["reply"] == "It is 4."
    assert len(santa.calls) == services.MAX_TOOL_ROUNDS + 1
    assert "tools" not in santa.calls[-1]["body"]  # the last round must answer


def test_a_server_that_rejects_tools_is_asked_again_without_them(client_for, student, santa):
    santa.reject_tools = True
    santa.script = [{"content": "Without the calculator: it's 4."}]
    events, _ = stream(client_for(student), message="2 + 2?")
    assert events[-1]["reply"] == "Without the calculator: it's 4."
    assert [bool(c["body"].get("tools")) for c in santa.calls] == [True, False]


def test_a_bare_expression_as_the_tool_argument_still_works(client_for, student, santa):
    santa.script = [{"content": "", "tool_calls": [("calculate", "6 * 7")]}, {"content": "It is 42."}]
    response = ask(client_for(student), message="6 * 7?")
    assert response.data["tools"] == [{"expression": "6 * 7", "result": "42"}]


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize(
    "shape",
    [
        {"choices": ["text"]},
        {"choices": [{"message": "text", "delta": "text"}]},
        {"choices": [{"message": {"content": 5}, "delta": {"content": 5}}]},
        {"choices": [{"message": {"tool_calls": ["x"]}, "delta": {"tool_calls": ["x"]}}]},
        {"choices": [], "usage": {"prompt_tokens": "many"}},
    ],
)
def test_a_reply_of_the_wrong_shape_answers_from_the_lessons(client_for, student, biology, santa, shape, streamed):
    santa.shape = shape
    client = client_for(student)
    if streamed:
        events, response = stream(client, message="cell membrane")
        done = events[-1]
    else:
        response = ask(client, message="cell membrane")
        done = response.data
    assert response.status_code == 200
    assert done["fallback"] == "unavailable" and "controls what enters" in done["reply"]
    assert TutorExchange.objects.get().stop_reason == "fallback:unavailable"


def test_a_question_too_long_for_the_model_is_asked_again_with_less(client_for, student, gradient_lesson, biology, santa):
    santa.too_long = 1
    santa.script = [{"content": "The membrane controls what goes in and out."}]
    history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hello! What shall we study?"}]
    said(student, "Hello! What shall we study?")
    response = ask(client_for(student), message="cell membrane gradient", history=history)
    assert response.data["reply"] == "The membrane controls what goes in and out."
    first, second = (c["body"] for c in santa.calls)
    assert "tools" in first and len(first["messages"]) == 4
    # Not mistaken for a server that refuses the calculator: no history, one passage and no tools.
    assert "tools" not in second and [m["role"] for m in second["messages"]] == ["system", "user"]
    assert second["messages"][1]["content"].count("\n[") == 1
    assert len(response.data["sources"]) == 1


def test_a_question_that_never_fits_answers_from_the_lessons(client_for, student, gradient_lesson, santa):
    santa.too_long = 5
    response = ask(client_for(student), message="linear graphs: gradient and intercept")
    assert len(santa.calls) == 2
    reply = response.data["reply"]
    assert response.data["fallback"] == "too_long" and "too long for Santa" in reply
    assert "rise over run" in reply and "crosses the y-axis" in reply  # all it found, not just what was sent last


def test_long_questions_leave_less_room_for_lesson_passages(student, unit):
    paragraph = "Photosynthesis makes glucose from carbon dioxide and water using light energy. " * 8
    for i in range(6):
        Lesson.objects.create(
            unit=unit, slug=f"plants-{i}", title=f"Plants {i}", status="published", body=f"## Part {i}\n\n{paragraph}"
        )
    question = "How does photosynthesis make glucose? " + "Please explain every step. " * 70
    history = [{"role": "user", "content": "x" * 1400}, {"role": "assistant", "content": "y" * 1400}] * 2
    said(student, "y" * 1400)
    roomy = services.prepare(student, "How does photosynthesis make glucose?")
    tight = services.prepare(student, question[: services.MAX_MESSAGE_CHARS], history=history)
    assert sum(len(p.text) for p in roomy.others) > services.MIN_PASSAGE_CHARS
    assert sum(len(p.text) for p in tight.others) <= services.MIN_PASSAGE_CHARS
    assert len(tight.history) < len(history)  # old turns make way
    written = sum(len(m["content"]) for m in tight.history) + len(tight.prompt)
    assert written <= services.TURN_CHARS + 500  # what is left is labels around the passages


def test_a_long_answer_says_it_ran_out_of_space(client_for, student, santa):
    santa.script = [{"content": "First, ", "finish_reason": "length"}]
    response = ask(client_for(student), message="Tell me everything")
    assert response.data["reply"].startswith("First, ") and "ran out of space" in response.data["reply"]


def test_an_answer_cut_half_way_keeps_what_arrived(client_for, student, santa):
    santa.script = [{"content": "The first part of a long answer."}]
    santa.cut_after = 2
    events, _ = stream(client_for(student), message="Explain")
    done = events[-1]
    assert done["reply"].startswith("The firs") and "stopped before finishing" in done["reply"]
    assert done["fallback"] is None


# Closing a stream ends the request, which closes the database connection as on a real server; only a
# transactional test can open a new one afterwards (on PostgreSQL; SQLite's in-memory test database stays open).
@pytest.mark.django_db(transaction=True)
def test_stopping_a_stream_logs_what_was_said(client_for, student, santa):
    santa.script = [{"content": "A long answer that the student stops."}]
    response = client_for(student).post("/api/tutor/stream/", {"message": "Explain"}, format="json")
    content = iter(response.streaming_content)
    next(content)  # start
    next(content)  # first piece of text
    response.close()  # Stop, as a browser does by closing the stream
    exchange = TutorExchange.objects.get()
    assert exchange.stop_reason == "stopped"
    assert cache.get(f"santa:user:{student.pk}") is None  # the student can ask again at once


def test_safety_net_always_gives_the_helpline(client_for, student, santa):
    santa.script = [{"content": "I'm sorry you feel this way."}]
    response = ask(client_for(student), message="I want to kill myself")
    assert "116" in response.data["reply"]
    response = ask(client_for(student), message="Je veux me tuer", lang="fr")
    assert "116" in response.data["reply"] and "adulte de confiance" in response.data["reply"]


# --- When the model can't answer: lesson passages ----------------------------------------------


def test_not_installed_answers_from_the_lessons(client_for, student, biology, settings):
    settings.SANTA_URL = ""
    response = ask(client_for(student), message="What does the cell membrane do?")
    assert response.status_code == 200
    assert response.data["fallback"] == "not_installed"
    reply = response.data["reply"]
    assert "not installed" in reply and "Here is what your lessons say" in reply
    assert "controls what enters and leaves" in reply
    assert response.data["sources"] == [
        {
            "slug": "the-cell",
            "title": "The cell",
            "section": "Parts of a cell",
            "subject": "Biology",
            "grade": "S1",
            "url": "/lessons/the-cell",
        }
    ]
    assert TutorExchange.objects.get().model == "lessons"


def test_a_loading_model_answers_from_the_lessons_in_french(client_for, student, biology, santa):
    santa.loading = True
    events, _ = stream(client_for(student), message="À quoi sert la membrane cellulaire ?", lang="fr")
    done = events[-1]
    assert done["fallback"] == "loading"
    assert "La membrane cellulaire contrôle" in done["reply"] and "se réveille" in done["reply"]
    assert done["sources"][0]["title"] == "La cellule"
    assert TutorExchange.objects.get().stop_reason == "fallback:loading"


def test_an_unreachable_model_answers_from_the_lessons(client_for, student, biology, settings):
    with socket.socket() as probe:  # a port nothing listens on
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    settings.SANTA_URL = f"http://127.0.0.1:{port}"
    response = ask(client_for(student), message="cell membrane")
    assert response.data["fallback"] == "unavailable" and "controls what enters" in response.data["reply"]
    assert llm.cached_health() == "unreachable"


def test_a_slow_model_times_out_and_answers_from_the_lessons(client_for, student, biology, santa, settings):
    settings.SANTA_TIMEOUT_SECONDS = 1
    santa.delay = 2.5
    started = time.monotonic()
    response = ask(client_for(student), message="cell membrane")
    assert response.data["fallback"] == "unavailable"
    assert time.monotonic() - started < 2.4


def test_a_bad_reply_answers_from_the_lessons(client_for, student, biology, santa):
    santa.garbage = True
    response = ask(client_for(student), message="cell membrane")
    assert response.data["fallback"] == "unavailable" and "controls what enters" in response.data["reply"]


def test_a_wrong_api_key_answers_from_the_lessons(client_for, student, biology, santa, settings):
    settings.SANTA_API_KEY = "wrong"
    response = ask(client_for(student), message="cell membrane")
    assert response.data["fallback"] == "unavailable"


def test_when_every_slot_is_busy_santa_answers_from_the_lessons(client_for, student, biology, santa, settings):
    settings.SANTA_PARALLEL = 1
    cache.add("santa:slot:0", "someone else", 60)
    response = ask(client_for(student), message="cell membrane")
    assert response.data["fallback"] == "busy" and santa.calls == []


def test_no_matching_lesson_says_so(client_for, student, settings):
    settings.SANTA_URL = ""
    response = ask(client_for(student), message="Who won the football match yesterday?")
    assert response.data["sources"] == [] and "couldn't find this in your lessons" in response.data["reply"]


def test_one_answer_at_a_time(client_for, student, santa):
    cache.add(f"santa:user:{student.pk}", 1, 60)
    response = ask(client_for(student), message="hello")
    assert response.status_code == 429 and response.data["code"] == "already_answering"
    events, _ = stream(client_for(student), message="hello")
    assert events == [{"type": "error", "code": "already_answering", "detail": response.data["detail"]}]


# --- Lesson passages ---------------------------------------------------------------------------


def test_retrieval_finds_the_relevant_lessons(student, gradient_lesson, biology):
    own, others = retrieval.search(student, "What does the cell membrane control?", "en")
    assert own == [] and others[0].slug == "the-cell" and others[0].language == "en"
    _, others = retrieval.search(student, "What is the gradient?", "en")
    assert others[0].slug == "linear" and others[0].heading == "Gradient"
    _, french = retrieval.search(student, "membrane cellulaire", "fr")
    assert french[0].language == "fr" and french[0].title == "La cellule"
    # A translated lesson is quoted in the reply language only, not the same section twice.
    _, once = retrieval.search(student, "À quoi sert la membrane cellulaire ?", "fr")
    assert [p.language for p in once] == ["fr"]
    _, once = retrieval.search(student, "cell membrane, la membrane cellulaire", "en")
    assert [p.language for p in once] == ["en"]
    # A lesson with no French yet is still quoted for a French question.
    _, english_only = retrieval.search(student, "Quel est le gradient ?", "fr")
    assert english_only[0].slug == "linear" and english_only[0].language == "en"
    # Questions about nothing in the lessons, or about studying in general, bring up nothing.
    assert retrieval.search(student, "Who won the football match yesterday?", "en") == ([], [])
    assert retrieval.search(student, "Explain this lesson more simply", "en") == ([], [])


def test_lessons_for_much_older_students_rank_lower(student, subject):
    body = "## Respiration\n\nCells release energy from glucose by respiration."
    for grade in ("S1", "S6"):  # on equal scores the later one would come first
        unit = Unit.objects.create(subject=subject, grade=grade, number=1, title="Energy")
        Lesson.objects.create(unit=unit, slug=f"energy-{grade}", title="Energy", status="published", body=body)
    _, others = retrieval.search(student, "How do cells release energy?", "en")  # the student is in S2
    assert [p.slug for p in others] == ["energy-S1", "energy-S6"]


def test_the_open_lesson_comes_first_in_reading_order(student, gradient_lesson, biology):
    own, others = retrieval.search(student, "Where does the line cross the y-axis?", "en", lesson=gradient_lesson)
    assert [p.heading for p in own] == ["Gradient", "The y-intercept"]
    assert all(p.slug != "linear" for p in others)


def test_retrieval_only_quotes_lessons_the_student_may_read(student, unit, biology):
    Lesson.objects.create(unit=unit, slug="draft", title="Draft", body="## Osmosis\n\nWater moves by osmosis.", status="draft")
    assert retrieval.search(student, "osmosis water", "en") == ([], [])
    unpaid = make_user("unpaid", school=make_school("Unpaid", "Huye"))
    biology.is_free = False
    biology.save()
    assert retrieval.search(unpaid, "cell membrane", "en")[1] == []
    biology.is_free = True
    biology.save()
    assert retrieval.search(unpaid, "cell membrane", "en")[1][0].slug == "the-cell"


def test_the_index_is_rebuilt_when_lessons_change(student, unit):
    assert retrieval.search(student, "photosynthesis chlorophyll", "en") == ([], [])
    lesson = Lesson.objects.create(
        unit=unit, slug="plants", title="Plants", status="published", body="## Photosynthesis\n\nChlorophyll traps light."
    )
    assert retrieval.search(student, "photosynthesis chlorophyll", "en")[1][0].slug == "plants"
    lesson.delete()
    assert retrieval.search(student, "photosynthesis chlorophyll", "en") == ([], [])


def test_lesson_text_is_cleaned_and_split_at_headings():
    body = (
        "Intro text.\n\n```sim\nfunction-grapher\n```\n\n## One\n\nSee [the lab](https://x.y) and ![a](b.png).\n\n## Two\n\nMore."
    )
    assert retrieval.split(body) == [("", "Intro text."), ("One", "See the lab and ."), ("Two", "More.")]


# --- The calculator ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("expression", "result"),
    [
        ("12 * 7", "84"),
        ("1/3 + 1/6", "0.5"),
        ("0.1 + 0.2", "0.3"),
        ("2/3", "2/3 (≈ 0.666666666667)"),
        ("2^10", "1024"),
        ("(3/4 + 2/5) * 12", "13.8"),
        ("sqrt(16)", "4"),
        ("sqrt(2)", "1.41421356237"),
        ("16 ** 0.5", "4"),
        ("sin(radians(30))", "0.5"),
        ("log(1000, 10)", "3"),
        ("7 % 3", "1"),
        ("-3/8", "-0.375"),
        ("factorial(5)", "120"),
        ("gcd(12, 18)", "6"),
        ("5 − 2 × 3 ÷ 4", "3.5"),
        ("pi * 2**2", "12.5663706144"),
        # Rounding as taught at school: a half goes away from zero.
        ("round(2.5)", "3"),
        ("round(-2.5)", "-3"),
        ("round(0.125, 2)", "0.13"),
        ("round(2.675, 2)", "2.68"),
        ("round(1234, -2)", "1200"),
        ("round(sqrt(2), 3)", "1.414"),
        ("floor(-2.5)", "-3"),
        ("round(10 ** 200 + 0.5)", "1e200"),
    ],
)
def test_calculator(expression, result):
    assert calculator.calculate(expression) == result


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('ls')",
        "().__class__.__bases__[0].__subclasses__()",
        "open('/etc/passwd').read()",
        "lambda: 1",
        "[x for x in range(10)]",
        "pi.real",
        "round(x=1)",
        "x + 1",
        "'a' * 3",
        "True + 1",
        "1 if 1 else 2",
        "9 ** 9 ** 9",
        "10 ** 10 ** 10",
        "10 ** 400",
        "(10 ** 200) * (10 ** 200)",
        "factorial(100000)",
        "1e308 * 10",
        "1 / 0",
        "sqrt(-1)",
        "(-8) ** (1/3)",
        "1 +",
        "(" * 150 + "1" + ")" * 150,
        "1" + " + 1" * 80,
        "1" * 300,
    ],
)
def test_the_calculator_refuses_anything_else(expression, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("eval and exec must never run")

    monkeypatch.setattr(builtins, "eval", forbidden)
    monkeypatch.setattr(builtins, "exec", forbidden)
    started = time.monotonic()
    assert calculator.calculate(expression).startswith("error: ")
    assert time.monotonic() - started < 1


@pytest.mark.parametrize(
    ("expression", "result"),
    [("0.5 ** (1000000000001/2)", "0"), ("2 ** (-1000000000001/2)", "0"), ("1 ** (10 ** 150 + 1/2)", "1")],
)
def test_huge_powers_stay_quick(expression, result):
    started = time.monotonic()
    assert calculator.calculate(expression) == result
    assert time.monotonic() - started < 1


# --- What Santa may see, and the exam lock ------------------------------------------------------


def test_draft_lesson_is_not_shared_with_santa(client_for, student, unit, santa):
    Lesson.objects.create(unit=unit, slug="draft", title="Draft", body="secret", status="draft")
    response = ask(client_for(student), lesson="draft")
    assert response.status_code == 404
    assert santa.calls == []


def _start(client, quiz):
    return client.post(f"/api/quizzes/{quiz.id}/start/").data


def test_santa_is_off_during_exams(client_for, student, subject, unit, santa):
    quiz = make_quiz(subject, unit, [add_mcq(subject, unit)], feedback_mode="after_submit")
    client = client_for(student)
    attempt = _start(client, quiz)
    for send in (ask, stream):
        response = send(client, message="answer?", attempt=attempt["id"], question=attempt["questions"][0]["id"])
        response = response[1] if isinstance(response, tuple) else response
        assert response.status_code == 403
    assert santa.calls == []


def test_practice_question_in_progress_never_shares_the_answer(client_for, student, subject, unit, santa):
    question = add_mcq(subject, unit, "What is 7 x 8?", "fifty-six", ("forty-eight", "sixty-four"))
    question.explanation = "SECRET-EXPLANATION"
    question.save()
    quiz = make_quiz(subject, unit, [question], feedback_mode="immediate")
    client = client_for(student)
    attempt = _start(client, quiz)
    response = ask(client, message="hint please", attempt=attempt["id"], question=question.id)
    assert response.status_code == 200
    prompt = last_prompt(santa)
    assert "STILL ANSWERING" in prompt and "What is 7 x 8?" in prompt
    assert "SECRET-EXPLANATION" not in prompt
    assert "Correct option" not in prompt


def test_after_submitting_santa_sees_the_solution(client_for, student, subject, unit, santa):
    question = add_mcq(subject, unit, "What is 7 x 8?", "fifty-six", ("forty-eight", "sixty-four"))
    quiz = make_quiz(subject, unit, [question], feedback_mode="after_submit")
    client = client_for(student)
    attempt = _start(client, quiz)
    wrong = question.choices.get(text="forty-eight").id
    client.post(f"/api/attempts/{attempt['id']}/answer/", {"question": question.id, "choice_ids": [wrong]}, format="json")
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    response = ask(client, message="why?", attempt=attempt["id"], question=question.id)
    assert response.status_code == 200
    prompt = last_prompt(santa)
    assert "Correct option(s): fifty-six" in prompt
    assert "Student's answer: forty-eight" in prompt


def test_cannot_ask_about_someone_elses_attempt(client_for, student, other_student, quiz_factory, santa):
    attempt = _start(client_for(student), quiz_factory(feedback_mode="immediate"))
    response = ask(client_for(other_student), attempt=attempt["id"])
    assert response.status_code == 404


def test_history_must_alternate_and_is_trimmed(client_for, student, santa):
    bad = [{"role": "assistant", "content": "hi"}, {"role": "assistant", "content": "again"}]
    assert ask(client_for(student), history=bad).status_code == 400
    good = [{"role": "user", "content": "What is a cell?"}, {"role": "assistant", "content": "The unit of life."}]
    said(student, "The unit of life.")
    assert ask(client_for(student), message="More?", history=good).status_code == 200
    assert [m["role"] for m in santa.calls[-1]["body"]["messages"]] == ["system", "user", "assistant", "user"]
    # Old turns that don't fit Santa's memory are left out, a question and its answer together.
    long = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"turn {i} " + "x" * 1400} for i in range(6)]
    said(student, *(m["content"] for m in long[1::2]))
    ask(client_for(student), message="And now?", history=long)
    sent = santa.calls[-1]["body"]["messages"][1:-1]
    assert sent[0]["content"].startswith("turn 4") and len(sent) == 2


def test_replies_in_the_students_language(client_for, student, santa):
    student.preferred_language = "fr"
    student.save()
    ask(client_for(student), message="Seli ni nini?")
    assert "Reply in French" in last_prompt(santa)


def test_santa_follows_the_reading_language(client_for, student, gradient_lesson, santa):
    LessonTranslation.objects.create(
        lesson=gradient_lesson, language="fr", title="Graphiques", body="## La pente\n\nCORPS EN FRANÇAIS"
    )
    response = ask(client_for(student), message="Explique", lesson=gradient_lesson.slug, lang="fr")
    assert response.status_code == 200
    prompt = last_prompt(santa)
    assert "Reply in French" in prompt and "CORPS EN FRANÇAIS" in prompt and "rise over run" not in prompt
    assert response.data["sources"][0]["title"] == "Graphiques"


def test_santa_page_sends_the_chosen_subject(client_for, student, subject, santa):
    response = ask(client_for(student), message="What is a ratio?", subject=subject.code)
    assert response.status_code == 200
    assert "chose the subject Mathematics" in last_prompt(santa)
    assert TutorExchange.objects.get().subject == subject


def test_santa_page_rejects_an_unknown_subject(client_for, student, santa):
    response = ask(client_for(student), subject="astrology")
    assert response.status_code == 404
    assert santa.calls == []


def test_no_santa_anywhere_while_a_timed_test_is_open(client_for, student, subject, unit, lesson, santa):
    """A timed test in one tab switches Santa off on the Santa page and in lessons too."""
    quiz = make_quiz(subject, unit, [add_mcq(subject, unit)], feedback_mode="immediate", time_limit_minutes=20)
    client = client_for(student)
    attempt = _start(client, quiz)
    for extra in ({"subject": subject.code}, {"lesson": lesson.slug}, {}):
        assert ask(client, message="answer?", **extra).status_code == 403
        assert stream(client, message="answer?", **extra)[1].status_code == 403
    assert santa.calls == []

    client.post(f"/api/attempts/{attempt['id']}/submit/")
    assert ask(client, message="now?", subject=subject.code).status_code == 200


def test_an_expired_timed_test_does_not_keep_santa_off(client_for, student, subject, unit, santa):
    from datetime import timedelta

    from django.utils import timezone

    from apps.assessments.models import Attempt

    quiz = make_quiz(subject, unit, [add_mcq(subject, unit)], time_limit_minutes=10)
    client = client_for(student)
    attempt = _start(client, quiz)
    Attempt.objects.filter(pk=attempt["id"]).update(deadline=timezone.now() - timedelta(hours=1))
    assert ask(client, subject=subject.code).status_code == 200
    assert Attempt.objects.get(pk=attempt["id"]).status != Attempt.Status.IN_PROGRESS


def test_an_open_exam_mode_quiz_keeps_santa_off_until_submitted(client_for, student, subject, unit, santa):
    from datetime import timedelta

    from apps.assessments.models import Attempt

    quiz = make_quiz(subject, unit, [add_mcq(subject, unit)], feedback_mode="after_submit", title="Class test")
    client = client_for(student)
    attempt = _start(client, quiz)
    # Even the next day: the exam is still open, so Santa stays off and says what to submit.
    Attempt.objects.filter(pk=attempt["id"]).update(
        started_at=Attempt.objects.get(pk=attempt["id"]).started_at - timedelta(days=1)
    )
    response = ask(client)
    assert response.status_code == 403 and "Class test" in response.data["detail"]
    assert str(response.data["attempt"]) == str(attempt["id"])  # so the app can link to it
    client.post(f"/api/attempts/{attempt['id']}/submit/")
    assert ask(client).status_code == 200


def test_an_exam_the_student_can_no_longer_open_does_not_lock_santa(client_for, student, subject, unit, santa):
    from apps.assessments.models import Attempt

    quiz = make_quiz(subject, unit, [add_mcq(subject, unit)], feedback_mode="after_submit")
    client = client_for(student)
    attempt = _start(client, quiz)
    quiz.status = "archived"
    quiz.save()
    assert ask(client).status_code == 200
    assert Attempt.objects.get(pk=attempt["id"]).status != Attempt.Status.IN_PROGRESS


# --- The client on its own ---------------------------------------------------------------------


def test_the_stream_reader_follows_the_wire_format(santa, settings):
    santa.script = [{"content": "abcdefgh", "tool_calls": [("calculate", {"expression": "1+1"})]}]
    chunks = llm.chat_stream({"model": "santa", "messages": [{"role": "user", "content": "hi"}]}, time.monotonic() + 10)
    pieces = []
    try:
        while True:
            pieces.append(next(chunks))
    except StopIteration as done:
        reply = done.value
    assert "" in pieces  # the ": keep-alive" comment, passed on as a ping
    assert "".join(pieces) == "abcdefgh" and reply.content == "abcdefgh"
    assert reply.tool_calls == [{"id": "call_0", "name": "calculate", "arguments": '{"expression": "1+1"}'}]
    assert reply.finish_reason == "tool_calls" and reply.prompt_tokens == 120 and reply.completion_tokens == 40


def test_the_client_names_each_problem(santa, settings):
    payload = {"model": "santa", "messages": [{"role": "user", "content": "hi"}]}
    santa.loading = True
    with pytest.raises(llm.Loading):
        llm.chat(payload, time.monotonic() + 5)
    santa.loading = False
    santa.reject_tools = True
    with pytest.raises(llm.ToolsRejected):
        llm.chat({**payload, "tools": [calculator.TOOL]}, time.monotonic() + 5)
    settings.SANTA_URL = ""
    with pytest.raises(llm.NotInstalled):
        llm.chat(payload, time.monotonic() + 5)
