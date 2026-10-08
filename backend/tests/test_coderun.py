"""C++ and Java go to Iga's code runner (coderunner/server.py, tested on its own in coderunner/test_server.py).
Here a small fake runner answers over real HTTP, so these tests cover Django's side: access, sessions, errors."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

pytestmark = pytest.mark.django_db


class FakeRunner(BaseHTTPRequestHandler):
    calls = []
    sessions = {}
    status = 200
    token = None

    def log_message(self, *args):
        pass

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeRunner.calls.append((self.path, body, self.headers.get("Authorization")))
        if FakeRunner.status != 200:
            return self._send(FakeRunner.status, {"error": "boom"})
        if self.path == "/run":
            if "BUSY" in body["code"]:
                return self._send(200, {"state": "finished", "verdict": "busy", "output": []})
            if "cin" in body["code"] or "Scanner" in body["code"]:
                FakeRunner.sessions["s1"] = True
                return self._send(200, {"session": "s1", "state": "waiting", "output": [{"stream": "stdout", "text": "Name? "}]})
            return self._send(
                200,
                {
                    "session": "s0",
                    "state": "finished",
                    "verdict": "ok",
                    "exit_code": 0,
                    "signal": None,
                    "output": [{"stream": "stdout", "text": "hello\n"}],
                },
            )
        if self.path == "/input":
            if not FakeRunner.sessions.pop(body["session"], None):
                return self._send(404, {"error": "no such session"})
            return self._send(
                200,
                {
                    "session": body["session"],
                    "state": "finished",
                    "verdict": "ok",
                    "exit_code": 0,
                    "signal": None,
                    "output": [{"stream": "stdout", "text": f"Muraho, {body['text']}!\n"}],
                },
            )
        if self.path == "/stop":
            FakeRunner.sessions.pop(body["session"], None)
            return self._send(200, {"stopped": True})
        return self._send(404, {"error": "not found"})


@pytest.fixture
def runner(settings):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeRunner)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    FakeRunner.calls, FakeRunner.sessions, FakeRunner.status = [], {}, 200
    settings.CODE_RUNNER_URL = f"http://127.0.0.1:{server.server_address[1]}"
    settings.CODE_RUNNER_TOKEN = "s3cret"
    yield FakeRunner
    server.shutdown()


def run(client, **body):
    return client.post("/api/code/run/", {"language": "cpp", "code": "int main(){}", **body}, format="json")


def test_status_and_switched_off(client_for, student, settings):
    settings.CODE_RUNNER_URL = ""
    client = client_for(student)
    assert client.get("/api/code/status/").data == {"enabled": False, "languages": ["cpp", "java"]}
    assert run(client).data["code"] == "not_configured"
    assert client.post("/api/code/input/", {"session": "x", "text": "a"}, format="json").status_code == 503


def test_a_program_that_needs_no_input(client_for, student, runner):
    response = run(client_for(student))
    assert response.status_code == 200
    assert response.data["state"] == "finished" and response.data["verdict"] == "ok"
    assert response.data["output"] == [{"stream": "stdout", "text": "hello\n"}]
    path, body, auth = runner.calls[0]
    assert (path, body, auth) == ("/run", {"language": "cpp", "code": "int main(){}"}, "Bearer s3cret")


def test_waiting_for_input_like_a_terminal(client_for, student, runner):
    client = client_for(student)
    first = run(client, code="cin >> name;")
    assert first.data["state"] == "waiting" and first.data["output"][0]["text"] == "Name? "
    last = client.post("/api/code/input/", {"session": first.data["session"], "text": "Aline"}, format="json")
    assert last.status_code == 200 and last.data["output"][0]["text"] == "Muraho, Aline!\n"
    again = client.post("/api/code/input/", {"session": first.data["session"], "text": "x"}, format="json")
    assert again.status_code == 410  # finished: Run starts it again


def test_nobody_else_can_answer_or_stop_a_students_program(client_for, student, other_student, runner):
    first = run(client_for(student), code="Scanner in;")
    intruder = client_for(other_student)
    assert intruder.post("/api/code/input/", {"session": first.data["session"], "text": "x"}, format="json").status_code == 410
    intruder.post("/api/code/stop/", {"session": first.data["session"]}, format="json")
    assert ("/stop", {"session": "s1"}, "Bearer s3cret") not in runner.calls
    assert runner.sessions == {"s1": True}


def test_starting_again_stops_the_waiting_program(client_for, student, runner):
    client = client_for(student)
    run(client, code="cin >> x;")
    run(client)
    assert ("/stop", {"session": "s1"}, "Bearer s3cret") in runner.calls


def test_runner_busy_down_or_broken(client_for, student, runner, settings):
    client = client_for(student)
    busy = run(client, code="BUSY")
    assert busy.status_code == 503 and busy.data["code"] == "busy"
    runner.status = 500
    assert run(client).status_code == 502
    settings.CODE_RUNNER_URL = "http://127.0.0.1:9"  # nothing listens there
    response = run(client)
    assert response.status_code == 503 and response.data["code"] == "unavailable"


def test_one_request_at_a_time_per_student(client_for, student, runner):
    from apps.coderun import services

    with services.one_request_at_a_time(student.pk):
        response = run(client_for(student))
    assert response.status_code == 429 and response.data["code"] == "already_running"


def test_input_is_checked(client_for, student, runner):
    client = client_for(student)
    assert run(client, language="python").status_code == 400
    assert run(client, code="x" * 20_001).status_code == 400
    assert run(client, code="").status_code == 400
    assert client.post("/api/code/input/", {"session": "s1", "text": "x" * 4001}, format="json").status_code == 400
    assert runner.calls == []


def test_needs_login(client_for, runner):
    assert client_for().post("/api/code/run/", {"language": "cpp", "code": "x"}, format="json").status_code == 401
