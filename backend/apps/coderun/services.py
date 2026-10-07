"""Run C++ and Java for the code playground on a Piston server (https://github.com/engineer-man/piston).

Student code never runs on the Django server. It is sent to Piston, which compiles and runs it in a
sandbox (isolate) with no network and with time, memory, process and output limits; those limits are
set in Piston's own configuration (see docker-compose.yml). Piston has no authentication, so it must be
reachable only from Django, ideally on its own small machine. CODE_RUNNER_URL points to it; when it
is empty, C++ and Java are switched off. Python and SQL run in the browser and never come here.
"""

import json
import urllib.error
import urllib.request
from contextlib import contextmanager

from django.conf import settings
from django.core.cache import cache

MAX_CODE_CHARS = 20_000
MAX_STDIN_CHARS = 8_000

# Our language codes -> Piston runtime, the version installed by `setup_code_runner`, and the file name.
# Piston adds the extension: C++ is compiled as main.cpp; Java runs Main.java with the source launcher,
# which starts the FIRST class in the file, so the class with main() must come first.
LANGUAGES = {
    "cpp": {"runtime": "c++", "version": "10.2.0", "file": "main", "package": "gcc"},
    "java": {"runtime": "java", "version": "15.0.2", "file": "Main", "package": "java"},
}


class RunnerUnavailable(Exception):
    """Piston could not be reached, or took too long."""


class RunnerError(Exception):
    """Piston answered with an error (for example, a runtime that isn't installed)."""


class AlreadyRunning(Exception):
    """This user already has a program running."""


class RunnerBusy(Exception):
    """Every run slot is taken."""


@contextmanager
def run_slot(user_id):
    """Allow one run per user and CODE_RUNNER_MAX_RUNNING runs in all, refusing at once instead of queueing.

    Each waiting run would hold a web-server thread, so without this a few accounts could tie up the
    whole API. Slots are cache keys that expire on their own, so a crashed request can't keep one."""
    ttl = int(settings.CODE_RUNNER_TIMEOUT_SECONDS) + 5
    user_key = f"coderun:user:{user_id}"
    if not cache.add(user_key, 1, ttl):
        raise AlreadyRunning
    slot = next(
        (f"coderun:slot:{i}" for i in range(settings.CODE_RUNNER_MAX_RUNNING) if cache.add(f"coderun:slot:{i}", 1, ttl)), None
    )
    if slot is None:
        cache.delete(user_key)
        raise RunnerBusy
    try:
        yield
    finally:
        cache.delete_many([slot, user_key])


def enabled():
    return bool(settings.CODE_RUNNER_URL)


# Piston is an internal service: never send requests to it through an outbound proxy.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(method, path, payload=None, timeout=None):
    url = settings.CODE_RUNNER_URL.rstrip("/") + path
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with _opener.open(req, timeout=timeout or settings.CODE_RUNNER_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode() or "null")
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read().decode()).get("message", "")
        except (ValueError, AttributeError):
            message = ""
        raise RunnerError(f"HTTP {exc.code}: {message}".strip()) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RunnerUnavailable(str(getattr(exc, "reason", exc))) from exc


def _stage(data):
    if not data:
        return None
    return {
        "stdout": data.get("stdout") or "",
        "stderr": data.get("stderr") or "",
        "code": data.get("code"),
        "signal": data.get("signal"),
        "status": data.get("status") or "",
    }


def verdict(compile_stage, run_stage):
    """One word the app turns into a plain-language message."""
    if compile_stage and compile_stage["code"] != 0:  # also None: stopped by a limit
        return "compile_time_limit" if compile_stage["status"] == "TO" else "compile_error"
    if not run_stage:
        return "compile_error"
    if run_stage["status"] == "TO":
        return "time_limit"
    if run_stage["status"] in ("OL", "EL"):  # stdout or stderr longer than Piston's output limit
        return "output_limit"
    if run_stage["signal"] == "SIGKILL":
        return "killed"  # usually the memory limit
    if run_stage["signal"] or run_stage["code"] not in (0, None):
        return "runtime_error"
    return "ok"


def run(language, code, stdin=""):
    """Compile and run one program; returns {verdict, compile, run}. Nothing is stored."""
    spec = LANGUAGES[language]
    data = request(
        "POST",
        "/api/v2/execute",
        {
            "language": spec["runtime"],
            "version": spec["version"],
            "files": [{"name": spec["file"], "content": code}],
            "stdin": stdin,
        },
    )
    compile_stage, run_stage = _stage(data.get("compile")), _stage(data.get("run"))
    if compile_stage and compile_stage["code"] != 0:
        run_stage = None  # Piston copies the failed compile stage into "run"; don't show it twice
    if language == "java" and run_stage and run_stage["code"] == 1 and "error: compilation failed" in run_stage["stderr"]:
        # Java has no separate compile stage: `java Main.java` compiles in memory, then runs.
        compile_stage, run_stage = run_stage, None
    return {"verdict": verdict(compile_stage, run_stage), "compile": compile_stage, "run": run_stage}
