"""Run C++ and Java for the code playground on Iga's code runner (the `coderunner` folder of this repository).

Student code never runs on the Django server. It is sent to the code runner, a separate container with no
internet access, which compiles it and runs it as an unprivileged user with time, memory, process and output
limits. A program runs until it ends or waits for keyboard input; the student's answer is then sent to the
same session, like a real terminal. CODE_RUNNER_URL points to the runner (empty = C++ and Java are off),
and CODE_RUNNER_TOKEN is the secret both sides share. Python and SQL run in the browser and never come here.

The runner is a costly, shared resource, so: only signed-in users reach it (or only members of subscribed
schools, with CODE_RUNNER_ACCESS=subscribed); each user's requests go one at a time and starting a program
ends their previous one, so nobody holds more than one session; per-minute throttles apply; and each user
has daily limits (Kigali time) on programs started and CPU seconds used (CODE_RUNNER_DAILY_RUNS,
CODE_RUNNER_DAILY_CPU_SECONDS), counted in CodeRunUsage from the CPU time the runner reports for each step.
"""

import json
import time
import urllib.error
import urllib.request
from contextlib import contextmanager

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.schools import access

from .models import CodeRunUsage

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


def may_use(user):
    """Whether this user may run C++ and Java: every signed-in user, or with CODE_RUNNER_ACCESS=subscribed (or any
    other value, so a typo locks down rather than opens up) members of a subscribed school and platform admins."""
    return settings.CODE_RUNNER_ACCESS == "signed_in" or access.has_premium(user)


# --- Daily limits ------------------------------------------------------------------------------------


def _today():
    return timezone.localdate()


def _used_today(user_id):
    row = CodeRunUsage.objects.filter(user_id=user_id, day=_today()).values("runs", "cpu_ms").first()
    return row or {"runs": 0, "cpu_ms": 0}


def limit_reached(user_id, starting):
    """True when the user may not start a program (`starting`) or go on with one today."""
    used = _used_today(user_id)
    if starting and settings.CODE_RUNNER_DAILY_RUNS and used["runs"] >= settings.CODE_RUNNER_DAILY_RUNS:
        return True
    return bool(settings.CODE_RUNNER_DAILY_CPU_SECONDS and used["cpu_ms"] >= settings.CODE_RUNNER_DAILY_CPU_SECONDS * 1000)


def allowance(user_id):
    """What is left today: {"runs_left_today", "cpu_seconds_left_today"} (None = no limit)."""
    used = _used_today(user_id)
    runs, cpu = settings.CODE_RUNNER_DAILY_RUNS, settings.CODE_RUNNER_DAILY_CPU_SECONDS
    return {
        "runs_left_today": max(0, runs - used["runs"]) if runs else None,
        "cpu_seconds_left_today": max(0, cpu - used["cpu_ms"] // 1000) if cpu else None,
    }


def record(user_id, run=False, cpu_ms=0, limited=False):
    """Count a program started (`run`), the CPU time a step used, or a refusal because a limit was reached."""
    try:
        with transaction.atomic():
            row, _ = CodeRunUsage.objects.get_or_create(user_id=user_id, day=_today())
    except IntegrityError:  # created by another request at the same moment
        row = CodeRunUsage.objects.get(user_id=user_id, day=_today())
    changes = {"cpu_ms": F("cpu_ms") + max(0, int(cpu_ms))}
    if run:
        changes["runs"] = F("runs") + 1
    if limited:
        changes["limited"] = F("limited") + 1
    CodeRunUsage.objects.filter(pk=row.pk).update(**changes)


def _charge(user_id, result, started_at, run=False):
    """Count a step the runner answered: the CPU time it reports (an older runner that doesn't say is charged
    the time the step took)."""
    if not result or result.get("verdict") == "busy":
        return
    cpu_ms = result.get("cpu_ms")
    if not isinstance(cpu_ms, int) or isinstance(cpu_ms, bool) or cpu_ms < 0:
        cpu_ms = int((time.monotonic() - started_at) * 1000)
    record(user_id, run=run, cpu_ms=cpu_ms)


def summary():
    """The code runner's use today, for platform admins, with the limits."""
    t = CodeRunUsage.objects.filter(day=_today()).aggregate(
        total_runs=Sum("runs"),
        total_cpu=Sum("cpu_ms"),
        total_limited=Sum("limited"),
        students=Count("user", distinct=True, filter=Q(runs__gt=0)),
    )
    return {
        "today": {
            "runs": t["total_runs"] or 0,
            "cpu_seconds": round((t["total_cpu"] or 0) / 1000),
            "limited": t["total_limited"] or 0,
            "students": t["students"],
        },
        "limits": {
            "daily_runs": settings.CODE_RUNNER_DAILY_RUNS,
            "daily_cpu_seconds": settings.CODE_RUNNER_DAILY_CPU_SECONDS,
            "access": settings.CODE_RUNNER_ACCESS,
        },
    }


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
    started_at = time.monotonic()
    result = request("POST", "/run", {"language": language, "code": code})
    _remember(user_id, result)
    _charge(user_id, result, started_at, run=True)
    return result


def send_input(user_id, session_id, text):
    started_at = time.monotonic()
    result = request("POST", "/input", {"session": session_id, "text": text})
    if result is None:
        cache.delete(_session_key(session_id))
    _remember(user_id, result)
    _charge(user_id, result, started_at)
    return result


def stop(user_id, session_id):
    if owns(user_id, session_id):
        cache.delete(_session_key(session_id))
        try:
            request("POST", "/stop", {"session": session_id}, timeout=5)
        except (RunnerUnavailable, RunnerError):
            pass  # the runner ends idle sessions by itself
