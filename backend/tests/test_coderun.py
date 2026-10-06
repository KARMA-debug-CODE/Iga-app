"""C++ and Java runs go to a Piston server. Here a small fake Piston answers over real HTTP."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.core.management import CommandError, call_command

pytestmark = pytest.mark.django_db


class FakePiston(BaseHTTPRequestHandler):
    runtimes = []
    executed = []
    installed = []
    reply = None
    status = 200

    def log_message(self, *args):
        pass

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/v2/runtimes":
            return self._send(200, FakePiston.runtimes)
        return self._send(404, {"message": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/v2/execute":
            FakePiston.executed.append(body)
            return self._send(FakePiston.status, FakePiston.reply)
        if self.path == "/api/v2/packages":
            FakePiston.installed.append(body)
            return self._send(200, {"language": body["language"], "version": body["version"]})
        return self._send(404, {"message": "not found"})


@pytest.fixture
def piston(settings):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakePiston)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    FakePiston.runtimes, FakePiston.executed, FakePiston.installed, FakePiston.status = [], [], [], 200
    FakePiston.reply = {"run": {"stdout": "Muraho, Aline!\n", "stderr": "", "code": 0, "signal": None, "status": None}}
    settings.CODE_RUNNER_URL = f"http://127.0.0.1:{server.server_address[1]}"
    yield FakePiston
    server.shutdown()


def run(client, **body):
    return client.post("/api/code/run/", {"language": "cpp", "code": "int main(){}", **body}, format="json")


def test_status_and_switched_off(client_for, student, settings):
    settings.CODE_RUNNER_URL = ""
    client = client_for(student)
    assert client.get("/api/code/status/").data == {"enabled": False, "languages": ["cpp", "java"]}
    response = run(client)
    assert response.status_code == 503 and response.data["code"] == "not_configured"


def test_runs_cpp_with_input(client_for, student, piston):
    piston.reply["compile"] = {"stdout": "", "stderr": "", "code": 0, "signal": None, "status": None}
    response = run(client_for(student), code="#include <iostream>", stdin="Aline")
    assert response.status_code == 200
    assert response.data["verdict"] == "ok"
    assert response.data["run"]["stdout"] == "Muraho, Aline!\n"
    sent = piston.executed[0]
    assert sent["language"] == "c++" and sent["version"] == "10.2.0" and sent["stdin"] == "Aline"
    assert sent["files"] == [{"name": "main", "content": "#include <iostream>"}]


def test_java_is_sent_as_main(client_for, student, piston):
    run(client_for(student), language="java", code="public class Main {}")
    assert piston.executed[0]["language"] == "java" and piston.executed[0]["files"][0]["name"] == "Main"


@pytest.mark.parametrize(
    ("reply", "verdict"),
    [
        ({"compile": {"stdout": "", "stderr": "main.cpp:1: error", "code": 1, "signal": None}}, "compile_error"),
        ({"run": {"stdout": "", "stderr": "", "code": None, "signal": "SIGKILL", "status": "TO"}}, "time_limit"),
        ({"run": {"stdout": "aaaa", "stderr": "", "code": None, "signal": "SIGKILL", "status": "OL"}}, "output_limit"),
        ({"run": {"stdout": "", "stderr": "", "code": None, "signal": "SIGKILL", "status": "SG"}}, "killed"),
        ({"run": {"stdout": "", "stderr": "Exception in thread", "code": 1, "signal": None, "status": "RE"}}, "runtime_error"),
    ],
)
def test_problems_get_a_verdict(client_for, student, piston, reply, verdict):
    piston.reply = reply
    assert run(client_for(student)).data["verdict"] == verdict


def test_runner_down_or_broken(client_for, student, piston, settings):
    client = client_for(student)
    piston.status, piston.reply = 400, {"message": "c++-10.2.0 runtime is unknown"}
    response = run(client)
    assert response.status_code == 502 and response.data["code"] == "error"

    settings.CODE_RUNNER_URL = "http://127.0.0.1:9"  # nothing listens there
    response = run(client)
    assert response.status_code == 503 and response.data["code"] == "unavailable"


def test_input_is_checked(client_for, student, piston):
    client = client_for(student)
    assert run(client, language="python").status_code == 400
    assert run(client, code="x" * 20_001).status_code == 400
    assert run(client, code="").status_code == 400
    assert piston.executed == []


def test_needs_login(client_for, piston):
    assert client_for().post("/api/code/run/", {"language": "cpp", "code": "x"}, format="json").status_code == 401


def test_setup_installs_only_missing_runtimes(piston):
    piston.runtimes = [{"language": "c++", "version": "10.2.0", "aliases": ["cpp"]}]
    call_command("setup_code_runner")
    assert piston.installed == [{"language": "java", "version": "15.0.2"}]


def test_setup_needs_a_runner(settings):
    settings.CODE_RUNNER_URL = ""
    with pytest.raises(CommandError):
        call_command("setup_code_runner")
    call_command("setup_code_runner", "--skip-if-off")  # Docker Compose with C++/Java switched off
