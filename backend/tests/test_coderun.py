"""C++ and Java go to Iga's code runner (coderunner/server.py, tested on its own in coderunner/test_server.py).
Here a small fake runner answers over real HTTP, so these tests cover Django's side: access, sessions, errors."""

import json
import threading
import time
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.utils import timezone

from apps.coderun.models import CodeRunUsage
from apps.core.models import AuditLog

from .conftest import make_user

pytestmark = pytest.mark.django_db


class FakeRunner(BaseHTTPRequestHandler):
    calls = []
    sessions = {}
    status = 200
    token = None
    cpu_ms = None  # the CPU time each step reports (None: an older runner that doesn't say)
    delay = 0

    def log_message(self, *args):
        pass

    def _send(self, status, body):
        if status == 200 and FakeRunner.cpu_ms is not None and "state" in body:
            body = {**body, "cpu_ms": FakeRunner.cpu_ms}
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeRunner.calls.append((self.path, body, self.headers.get("Authorization")))
        if FakeRunner.delay:
            time.sleep(FakeRunner.delay)
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
    FakeRunner.cpu_ms, FakeRunner.delay = None, 0
    settings.CODE_RUNNER_URL = f"http://127.0.0.1:{server.server_address[1]}"
    settings.CODE_RUNNER_TOKEN = "s3cret"
    yield FakeRunner
    server.shutdown()


def run(client, **body):
    return client.post("/api/code/run/", {"language": "cpp", "code": "int main(){}", **body}, format="json")


def test_status_and_switched_off(client_for, student, settings):
    settings.CODE_RUNNER_URL = ""
    client = client_for(student)
    status = client.get("/api/code/status/").data
    assert (status["enabled"], status["languages"], status["allowed"]) == (False, ["cpp", "java"], True)
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


# --- Daily limits (CODE_RUNNER_DAILY_RUNS, CODE_RUNNER_DAILY_CPU_SECONDS) --------------------------------


def usage(user):
    return CodeRunUsage.objects.get(user=user, day=timezone.localdate())


def test_each_run_and_its_cpu_time_are_counted(client_for, student, runner):
    runner.cpu_ms = 250
    client = client_for(student)
    first = run(client, code="cin >> x;")
    client.post("/api/code/input/", {"session": first.data["session"], "text": "7"}, format="json")
    run(client)
    row = usage(student)
    assert (row.runs, row.cpu_ms, row.limited) == (2, 750, 0)  # two programs, three steps


def test_the_daily_run_limit(client_for, student, other_student, runner, settings):
    settings.CODE_RUNNER_DAILY_RUNS = 2
    client = client_for(student)
    assert run(client).status_code == run(client).status_code == 200
    calls = len(runner.calls)
    refused = run(client)
    assert refused.status_code == 429 and refused.data["code"] == "daily_limit"
    assert "used today's time on the code runner" in refused.data["detail"]
    assert len(runner.calls) == calls  # the runner was not asked
    assert usage(student).limited == 1
    assert AuditLog.objects.filter(action="code_run_limit", actor=student).count() == 1
    french = client.post("/api/code/run/", {"language": "cpp", "code": "x"}, format="json", HTTP_ACCEPT_LANGUAGE="fr")
    assert "serveur d'exécution du code" in french.data["detail"]
    assert run(client_for(other_student)).status_code == 200  # everyone has their own limit


def test_the_daily_cpu_limit_also_ends_a_waiting_program(client_for, student, runner, settings):
    settings.CODE_RUNNER_DAILY_CPU_SECONDS = 1
    runner.cpu_ms = 600
    client = client_for(student)
    assert run(client).status_code == 200  # 0.6 s
    waiting = run(client, code="cin >> name;")  # started under the limit: 1.2 s by the time it waits
    assert waiting.data["state"] == "waiting"
    refused = client.post("/api/code/input/", {"session": waiting.data["session"], "text": "Aline"}, format="json")
    assert refused.status_code == 429 and refused.data["code"] == "daily_limit"
    assert ("/stop", {"session": "s1"}, "Bearer s3cret") in runner.calls and runner.sessions == {}
    assert ("/input", {"session": "s1", "text": "Aline"}, "Bearer s3cret") not in runner.calls
    assert run(client).status_code == 429
    status = client.get("/api/code/status/").data
    assert status["allowance"] == {"runs_left_today": 298, "cpu_seconds_left_today": 0}


def test_an_older_runner_is_charged_the_time_a_step_took(client_for, student, runner):
    runner.delay = 0.3
    run(client_for(student))
    assert usage(student).cpu_ms >= 300


def test_busy_runs_are_free_and_a_new_day_starts_afresh(client_for, student, runner, settings):
    settings.CODE_RUNNER_DAILY_RUNS = 1
    CodeRunUsage.objects.create(user=student, day=timezone.localdate() - timedelta(days=1), runs=500, cpu_ms=10**7)
    client = client_for(student)
    assert run(client, code="BUSY").status_code == 503
    assert run(client).status_code == 200
    assert usage(student).runs == 1


def test_no_limit_when_set_to_zero(client_for, student, runner, settings):
    settings.CODE_RUNNER_DAILY_RUNS = settings.CODE_RUNNER_DAILY_CPU_SECONDS = 0
    CodeRunUsage.objects.create(user=student, day=timezone.localdate(), runs=10**6, cpu_ms=10**9)
    client = client_for(student)
    assert run(client).status_code == 200
    assert client.get("/api/code/status/").data["allowance"] == {"runs_left_today": None, "cpu_seconds_left_today": None}


# --- Who may use it (CODE_RUNNER_ACCESS) ------------------------------------------------------------------


@pytest.mark.parametrize("setting", ["subscribed", "Everyone?"])  # anything but "signed_in" locks down
def test_the_runner_can_be_kept_for_subscribed_schools(client_for, student, runner, settings, setting):
    settings.CODE_RUNNER_ACCESS = setting
    outsider = make_user("outsider", school=None)
    assert run(client_for(student)).status_code == 200
    refused = run(client_for(outsider))
    assert refused.status_code == 403 and refused.data["detail"].code == "subscription_required"
    first = run(client_for(student), code="cin >> x;")
    intruder = client_for(outsider).post("/api/code/input/", {"session": first.data["session"], "text": "x"}, format="json")
    assert intruder.status_code == 410  # not theirs anyway
    assert client_for(outsider).get("/api/code/status/").data["allowed"] is False
    assert len([c for c in runner.calls if c[0] == "/run"]) == 2


def test_by_default_every_signed_in_user_may_run_code(client_for, runner):
    assert run(client_for(make_user("outsider", school=None))).status_code == 200
    assert run(client_for(make_user("mum", role="parent"))).status_code == 200


# --- One session per user ---------------------------------------------------------------------------------


def test_a_user_never_holds_more_than_one_session(client_for, student, runner):
    client = client_for(student)
    for _ in range(3):
        assert run(client, code="cin >> x;").data["state"] == "waiting"
        assert len(runner.sessions) == 1  # each start ended the program before


def test_platform_admins_see_the_runner_use(client_for, student, admin_user, runner):
    runner.cpu_ms = 1500
    run(client_for(student))
    run(client_for(student))
    data = client_for(admin_user).get("/api/admin/stats/").data["code_runner"]
    assert data["today"] == {"runs": 2, "cpu_seconds": 3, "limited": 0, "students": 1}
    assert data["limits"] == {"daily_runs": 300, "daily_cpu_seconds": 900, "access": "signed_in"}
