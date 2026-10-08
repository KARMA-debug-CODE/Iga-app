"""Run C++ and Java for the code playground on Iga's code runner (the `coderunner` folder of this repository).

Student code never runs on the Django server. It is sent to the code runner, a separate container with no
internet access, which compiles it and runs it as an unprivileged user with time, memory, process and output
limits. A program runs until it ends or waits for keyboard input; the student's answer is then sent to the
same session, like a real terminal. CODE_RUNNER_URL points to the runner (empty = C++ and Java are off),
and CODE_RUNNER_TOKEN is the secret both sides share. Python and SQL run in the browser and never come here.
"""

import json
import urllib.error
import urllib.request
from contextlib import contextmanager

from django.conf import settings
from django.core.cache import cache

LANGUAGES = ("cpp", "java")
MAX_CODE_CHARS = 20_000
MAX_INPUT_CHARS = 4_000
# Each session belongs to the student who started it; kept as long as the runner keeps an idle session.
SESSION_TTL = 15 * 60


class RunnerUnavailable(Exception):
    """The code runner could not be reached, or took too long."""


class RunnerError(Exception):
    """The code runner answered with an error."""


class AlreadyRunning(Exception):
    """This student already has a request to the runner in progress."""


def enabled():
    return bool(settings.CODE_RUNNER_URL)


# The runner is an internal service: never send requests to it through an outbound proxy.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(method, path, payload=None, timeout=None):
    url = settings.CODE_RUNNER_URL.rstrip("/") + path
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if settings.CODE_RUNNER_TOKEN:
        headers["Authorization"] = f"Bearer {settings.CODE_RUNNER_TOKEN}"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with _opener.open(req, timeout=timeout or settings.CODE_RUNNER_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode() or "null")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RunnerError(f"HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RunnerUnavailable(str(getattr(exc, "reason", exc))) from exc


@contextmanager
def one_request_at_a_time(user_id):
    """A student's requests to the runner go one at a time (each holds a web-server thread while it waits)."""
    key = f"coderun:busy:{user_id}"
    if not cache.add(key, 1, int(settings.CODE_RUNNER_TIMEOUT_SECONDS) + 5):
        raise AlreadyRunning
    try:
        yield
    finally:
        cache.delete(key)


def _session_key(session_id):
    return f"coderun:session:{session_id}"


def _remember(user_id, result):
    """Keep track of a session that is waiting for input; forget it once the program has finished."""
    session_id = (result or {}).get("session")
    if not session_id:
        return
    if result.get("state") == "waiting":
        cache.set(_session_key(session_id), user_id, SESSION_TTL)
        cache.set(f"coderun:current:{user_id}", session_id, SESSION_TTL)
    else:
        cache.delete(_session_key(session_id))


def owns(user_id, session_id):
    return bool(session_id) and cache.get(_session_key(session_id)) == user_id


def run(user_id, language, code):
    """Start a program; returns the runner's step result (output so far, and whether it waits for input)."""
    previous = cache.get(f"coderun:current:{user_id}")
    if previous:
        stop(user_id, previous)  # one program per student: starting another ends the last one
    result = request("POST", "/run", {"language": language, "code": code})
    _remember(user_id, result)
    return result


def send_input(user_id, session_id, text):
    result = request("POST", "/input", {"session": session_id, "text": text})
    if result is None:
        cache.delete(_session_key(session_id))
    _remember(user_id, result)
    return result


def stop(user_id, session_id):
    if owns(user_id, session_id):
        cache.delete(_session_key(session_id))
        try:
            request("POST", "/stop", {"session": session_id}, timeout=5)
        except (RunnerUnavailable, RunnerError):
            pass  # the runner ends idle sessions by itself
