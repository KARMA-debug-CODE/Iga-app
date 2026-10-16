"""Tests of the nginx layer in front of Django (frontend/nginx.conf and frontend/nginx/).

They build the web image's nginx stage (no npm needed), start it next to a stub backend that answers every
request with what it received (stub_backend.py), on a private Docker network, and send requests to it on
127.0.0.1 only. Each test starts its own nginx with the settings it needs, so the limits start fresh.

Needs Docker and Python 3 (standard library only). Run from anywhere:
    python3 frontend/tests/nginx/test_nginx.py
"""

import concurrent.futures
import http.client
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.dirname(os.path.dirname(HERE))
RUN_ID = uuid.uuid4().hex[:8]
IMAGE = f"iga-nginx-test:{RUN_ID}"
NETWORK = f"iga-nginx-test-{RUN_ID}"
STUB_IMAGE = os.environ.get("NGINX_TEST_STUB_IMAGE", "python:3.12-slim")
JSON_TYPE = "application/json; charset=utf-8"

_containers = []
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HTML = SUBNET = GATEWAY = None


def docker(*args, check=True):
    result = subprocess.run(["docker", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"docker {' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def setUpModule():
    global HTML, SUBNET, GATEWAY
    docker("build", "-q", "--target", "web-base", "-t", IMAGE, FRONTEND)
    docker("network", "create", NETWORK)
    SUBNET = docker("network", "inspect", "-f", "{{(index .IPAM.Config 0).Subnet}}", NETWORK)
    GATEWAY = docker("network", "inspect", "-f", "{{(index .IPAM.Config 0).Gateway}}", NETWORK)
    _containers.append(
        docker(
            "run", "-d", "--network", NETWORK, "--network-alias", "backend",
            "-v", f"{HERE}/stub_backend.py:/stub.py:ro", STUB_IMAGE, "python", "/stub.py",
        )
    )  # fmt: skip
    # A stand-in for the built app.
    HTML = tempfile.mkdtemp(prefix="iga-nginx-html-")
    os.makedirs(os.path.join(HTML, "assets"))
    files = {
        "index.html": "<!doctype html><title>Iga</title><div id=root></div>",
        "assets/app-1234.js": "console.log('app');",
        "sw.js": "self.addEventListener('fetch', () => {});",
    }
    for name, text in files.items():
        with open(os.path.join(HTML, name), "w") as f:
            f.write(text)
    os.chmod(HTML, 0o755)
    for root, dirs, names in os.walk(HTML):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)
        for n in names:
            os.chmod(os.path.join(root, n), 0o644)


def tearDownModule():
    for container in _containers:
        docker("rm", "-f", container, check=False)
    docker("network", "rm", NETWORK, check=False)
    docker("rmi", IMAGE, check=False)
    if HTML:
        shutil.rmtree(HTML, ignore_errors=True)


class Response:
    def __init__(self, status, headers, body):
        self.status, self.headers, self.body = status, headers, body

    def json(self):
        return json.loads(self.body)

    def header(self, name):
        return self.headers.get(name)


class Nginx:
    """The web image's nginx with these settings (NGINX_* environment variables), on a free local port."""

    def __init__(self, extra_args=(), **env):
        args = ["run", "-d", "--network", NETWORK, "-p", "127.0.0.1::80", "-v", f"{HTML}:/usr/share/nginx/html:ro"]
        for name, value in env.items():
            args += ["-e", f"{name}={value}"]
        self.id = docker(*args, *extra_args, IMAGE)
        _containers.append(self.id)
        port = docker("port", self.id, "80/tcp").splitlines()[0].rsplit(":", 1)[1]
        self.host, self.port = "127.0.0.1", int(port)
        self.base = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 20
        while "start worker process" not in self.logs():
            if time.monotonic() > deadline or docker("inspect", "-f", "{{.State.Running}}", self.id) != "true":
                raise RuntimeError("nginx did not start:\n" + self.logs())
            time.sleep(0.2)

    def request(self, path, method="GET", body=None, headers=None, timeout=30):
        data = body.encode() if isinstance(body, str) else body
        request = urllib.request.Request(self.base + path, data=data, method=method, headers=headers or {})
        try:
            with _opener.open(request, timeout=timeout) as response:
                return Response(response.status, response.headers, response.read())
        except urllib.error.HTTPError as error:
            return Response(error.code, error.headers, error.read())

    def post_json(self, path, payload=None, headers=None):
        return self.request(path, "POST", json.dumps(payload or {}), {"Content-Type": "application/json", **(headers or {})})

    def logs(self):
        return _all_logs(self.id)


LOW_LIMITS = {
    "NGINX_RATE_AUTH": "6r/m",
    "NGINX_BURST_AUTH": "3",
    "NGINX_RATE_COSTLY": "6r/m",
    "NGINX_BURST_COSTLY": "2",
    "NGINX_RATE_API": "6r/m",
    "NGINX_BURST_API": "5",
}


class RateLimits(unittest.TestCase):
    """S4/S7: every API route is limited per client address, strictest on sign-in, and refusals are JSON."""

    def test_sign_in_flood_is_refused_with_json_429(self):
        nginx = Nginx(**LOW_LIMITS)
        statuses = [nginx.post_json("/api/auth/login/", {"identifier": f"u{i}"}).status for i in range(8)]
        # One request plus a burst of 3 reach Django; the rest are refused by nginx.
        self.assertEqual(statuses, [200] * 4 + [429] * 4)
        refused = nginx.post_json("/api/auth/login/")
        self.assertEqual(refused.status, 429)
        self.assertEqual(refused.header("Content-Type"), JSON_TYPE)
        self.assertEqual(refused.json(), {"detail": "Too many requests. Please wait a moment and try again."})
        self.assertGreater(int(refused.header("Retry-After")), 0)
        french = nginx.post_json("/api/auth/login/", headers={"Accept-Language": "fr"})
        self.assertEqual(french.json(), {"detail": "Trop de requêtes. Patientez un instant, puis réessayez."})

    def test_every_auth_route_shares_the_strict_limit(self):
        nginx = Nginx(**LOW_LIMITS)
        paths = ["/api/auth/register/", "/api/auth/password-reset/", "/api/auth/2fa/enable/", "/api/auth/step-up/"]
        statuses = [nginx.post_json(path).status for path in paths * 2]
        self.assertEqual(statuses, [200] * 4 + [429] * 4)

    def test_costly_routes_have_their_own_tight_limit(self):
        nginx = Nginx(**LOW_LIMITS)
        for path in ["/api/tutor/ask/", "/api/code/run/", "/api/billing/checkout/"]:
            statuses = [nginx.post_json(path).status for _ in range(5)]
            # Each costly route counts against one shared allowance: 1 + burst 2 in all.
            self.assertIn(429, statuses, path)
        # Santa's status and a running program's answers are ordinary API requests, not costly ones.
        self.assertEqual(nginx.request("/api/tutor/status/").status, 200)
        self.assertEqual(nginx.post_json("/api/code/input/").status, 200)

    def test_the_rest_of_the_api_is_limited_too(self):
        nginx = Nginx(**LOW_LIMITS)
        statuses = [nginx.request("/api/meta/").status for _ in range(9)]
        self.assertEqual(statuses, [200] * 6 + [429] * 3)

    def test_the_app_itself_is_not_rate_limited(self):
        nginx = Nginx(**LOW_LIMITS)
        statuses = {nginx.request(path).status for path in ["/", "/lessons/x", "/assets/app-1234.js"] * 15}
        self.assertEqual(statuses, {200})

    def test_too_many_santa_answers_at_once_from_one_address(self):
        nginx = Nginx(NGINX_CONN_PER_IP_TUTOR="2")
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            statuses = sorted(pool.map(lambda _: nginx.post_json("/api/tutor/stream/").status, range(4)))
        self.assertEqual(statuses, [200, 200, 429, 429])


class ClientAddress(unittest.TestCase):
    """S4/S7: only trusted proxies may say who the client is; a made-up header changes nothing."""

    SPOOFS = [
        {"X-Forwarded-For": "203.0.113.7"},
        {"X-Forwarded-For": "198.51.100.1, 203.0.113.8"},
        {"CF-Connecting-IP": "203.0.113.9"},
        {"X-Real-IP": "203.0.113.10"},
    ]

    def test_without_trusted_proxies_django_sees_the_connecting_address(self):
        nginx = Nginx()
        for spoof in self.SPOOFS:
            seen = nginx.request("/api/meta/", headers=spoof).json()["headers"]
            self.assertEqual(seen["x-forwarded-for"], GATEWAY, spoof)
            self.assertEqual(seen["x-real-ip"], GATEWAY, spoof)
            self.assertNotIn("cf-connecting-ip", seen)

    def test_a_made_up_header_does_not_buy_a_fresh_allowance(self):
        nginx = Nginx(**LOW_LIMITS)
        statuses = []
        for i in range(8):
            spoof = {"X-Forwarded-For": f"203.0.113.{i}", "CF-Connecting-IP": f"198.51.100.{i}"}
            statuses.append(nginx.post_json("/api/auth/login/", headers=spoof).status)
        self.assertEqual(statuses, [200] * 4 + [429] * 4)

    def test_a_trusted_proxy_names_the_client(self):
        nginx = Nginx(NGINX_TRUSTED_PROXIES=SUBNET, NGINX_REAL_IP_HEADER="CF-Connecting-IP", **LOW_LIMITS)
        seen = nginx.request("/api/meta/", headers={"CF-Connecting-IP": "41.186.1.9"}).json()["headers"]
        self.assertEqual(seen["x-forwarded-for"], "41.186.1.9")
        # Limits count per real client: a second client behind the same proxy has its own allowance.
        first = [nginx.post_json("/api/auth/login/", headers={"CF-Connecting-IP": "41.186.1.10"}).status for _ in range(5)]
        second = nginx.post_json("/api/auth/login/", headers={"CF-Connecting-IP": "41.186.1.11"}).status
        self.assertEqual(first, [200] * 4 + [429])
        self.assertEqual(second, 200)

    def test_cloudflare_ranges_are_not_trusted_for_anyone_else(self):
        # Trusting Cloudflare doesn't trust this test's address: the header is ignored.
        nginx = Nginx(NGINX_TRUSTED_PROXIES="cloudflare")
        seen = nginx.request("/api/meta/", headers={"CF-Connecting-IP": "41.186.1.9"}).json()["headers"]
        self.assertEqual(seen["x-forwarded-for"], GATEWAY)

    def test_the_origin_can_refuse_everyone_but_its_proxies(self):
        nginx = Nginx(NGINX_TRUSTED_PROXIES="cloudflare", NGINX_ONLY_FROM_TRUSTED_PROXIES="true")
        with self.assertRaises((urllib.error.URLError, ConnectionError, http.client.HTTPException)):
            _opener.open(nginx.base + "/", timeout=5).read()

    def test_a_bad_trusted_proxy_setting_stops_the_start(self):
        container = docker("run", "-d", "-e", "NGINX_TRUSTED_PROXIES=10.0.0.0/8;evil", IMAGE)
        _containers.append(container)
        self.assertEqual(docker("wait", container), "1")
        self.assertIn("is not an address", _all_logs(container))


def _seconds_until_closed(nginx, first_bytes, limit=40):
    """Send `first_bytes`, then nothing: how long until nginx gives up on this connection."""
    sock = socket.create_connection((nginx.host, nginx.port))
    sock.settimeout(limit)
    started = time.monotonic()
    sock.sendall(first_bytes)
    try:
        while sock.recv(4096):
            pass
    except (TimeoutError, ConnectionResetError):
        pass
    finally:
        sock.close()
    return time.monotonic() - started


class SlowClients(unittest.TestCase):
    """S9: a client that sends its request (or reads its answer) slowly can't hold a connection for long."""

    def test_slow_headers_slow_bodies_and_idle_connections_are_dropped(self):
        nginx = Nginx()  # the defaults: 10 s for the headers, 15 s between two reads of a body, 20 s idle
        cases = {
            "headers": b"GET /api/meta/ HTTP/1.1\r\nHost: localhost\r\n",
            "body": b"POST /api/meta/ HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
            b"Content-Length: 1000\r\n\r\n{",
            "idle": b"GET /sw.js HTTP/1.1\r\nHost: localhost\r\n\r\n",
        }
        with concurrent.futures.ThreadPoolExecutor(len(cases)) as pool:
            held = dict(zip(cases, pool.map(lambda data: _seconds_until_closed(nginx, data), cases.values()), strict=True))
        # nginx's own default would have been 60 s for headers and bodies, and 65 s for idle connections.
        self.assertTrue(9 <= held["headers"] <= 13, held)
        self.assertTrue(14 <= held["body"] <= 18, held)
        self.assertTrue(19 <= held["idle"] <= 23, held)

    def test_the_server_does_not_say_its_version(self):
        self.assertEqual(Nginx().request("/").header("Server"), "nginx")


class RequestSize(unittest.TestCase):
    """S22: bodies are small by default and larger only on upload routes; a bigger one never reaches Django."""

    @classmethod
    def setUpClass(cls):
        cls.nginx = Nginx()

    def post(self, path, size, **headers):
        return self.nginx.request(path, "POST", b"x" * size, {"Content-Type": "application/octet-stream", **headers})

    def test_json_api_bodies_are_capped_at_2_mb(self):
        accepted = self.post("/api/lessons/", 1_500_000)
        self.assertEqual((accepted.status, accepted.json()["body_bytes"]), (200, 1_500_000))
        refused = self.post("/api/lessons/", 3 * 1024 * 1024)
        self.assertEqual(refused.status, 413)
        self.assertEqual(refused.header("Content-Type"), JSON_TYPE)
        self.assertEqual(refused.json(), {"detail": "This request is too large."})
        french = self.post("/api/tutor/ask/", 3 * 1024 * 1024, **{"Accept-Language": "fr-FR,fr;q=0.9"})
        self.assertEqual(french.json(), {"detail": "Cette requête est trop volumineuse."})

    def test_sign_in_bodies_are_tiny(self):
        self.assertEqual(self.post("/api/auth/login/", 10_000).status, 200)
        self.assertEqual(self.post("/api/auth/login/", 100_000).status, 413)

    def test_only_upload_routes_take_files(self):
        self.assertEqual(self.post("/api/resources/", 10 * 1024 * 1024).status, 200)
        self.assertEqual(self.post("/api/resources/7/", 10 * 1024 * 1024).status, 200)
        self.assertEqual(self.post("/django-admin/secret/assessments/exampaper/add/", 10 * 1024 * 1024).status, 200)
        self.assertEqual(self.post("/api/resources/", 30 * 1024 * 1024).status, 413)
        self.assertEqual(self.post("/api/classes/1/import_roster/", 10 * 1024 * 1024).status, 413)

    def test_the_app_takes_no_bodies(self):
        self.assertEqual(self.post("/", 64 * 1024).status, 413)


def _all_logs(container):
    result = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
    return result.stdout + result.stderr


if __name__ == "__main__":
    unittest.main(verbosity=2)
