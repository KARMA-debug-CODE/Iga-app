"""gunicorn's settings for production (backend/gunicorn.conf.py), as the container's CMD loads them: threaded
workers, timeouts and request caps (S9). Slow clients never reach gunicorn: nginx reads requests whole first
(frontend/tests/nginx/test_nginx.py tests that part)."""

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def gunicorn_config(**env):
    result = subprocess.run(
        [sys.executable, "-m", "gunicorn", "--print-config", "config.wsgi:application"],
        cwd=BACKEND,
        # --print-config also loads the app: development settings are enough for that.
        env={"PATH": os.environ.get("PATH", ""), "DJANGO_DEBUG": "true", **env},
        capture_output=True,
        text=True,
        check=True,
    )
    values = {}
    for line in result.stdout.splitlines():
        name, sep, value = line.partition("=")
        if sep:
            values[name.strip()] = value.strip()
    return values


def test_threaded_workers_with_timeouts_and_request_caps():
    config = gunicorn_config()
    assert config["worker_class"] == "gthread"
    assert (config["workers"], config["threads"]) == ("3", "4")
    assert config["timeout"] == "60" and config["graceful_timeout"] == "30" and config["keepalive"] == "5"
    assert config["max_requests"] == "2000" and config["max_requests_jitter"] == "200"
    assert config["limit_request_line"] == "8190"
    assert config["limit_request_fields"] == "100"
    assert config["limit_request_field_size"] == "8190"
    assert config["bind"] == "['0.0.0.0:8000']"


def test_settings_come_from_the_environment():
    config = gunicorn_config(GUNICORN_WORKERS="5", GUNICORN_THREADS="8", GUNICORN_TIMEOUT="90")
    assert (config["workers"], config["threads"], config["timeout"]) == ("5", "8", "90")


def test_the_container_uses_this_file():
    cmd = next(line for line in (BACKEND / "Dockerfile").read_text().splitlines() if line.startswith("CMD"))
    assert "exec gunicorn config.wsgi:application" in cmd
    # Options on the command line would override the file.
    assert "--timeout" not in cmd and "--workers" not in cmd
