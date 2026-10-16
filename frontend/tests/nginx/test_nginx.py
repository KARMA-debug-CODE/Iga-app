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
import ssl
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.dirname(os.path.dirname(HERE))
RUN_ID = uuid.uuid4().hex[:8]
IMAGE = f"iga-nginx-test:{RUN_ID}"
NETWORK = f"iga-nginx-test-{RUN_ID}"
STUB_IMAGE = os.environ.get("NGINX_TEST_STUB_IMAGE", "python:3.12-slim")
JSON_TYPE = "application/json; charset=utf-8"

_containers = []


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # the test looks at the redirect itself


_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirects())
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
    os.makedirs(os.path.join(HTML, "pyodide"))
    files = {
        "index.html": "<!doctype html><title>Iga</title><div id=root></div>",
        "assets/app-1234.js": "console.log('app');",
        "assets/pyodide.worker-1234.js": "importScripts();",
        "pyodide/pyodide.mjs": "export {};",
        "sw.js": "self.addEventListener('fetch', () => {});",
        "playground-frame.html": "<!doctype html><title>Preview</title>",
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
        env = {"NGINX_FORCE_HTTPS": "false", **env}  # plain HTTP, as in the local trial, unless a test says otherwise
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

    def request(self, path, method="GET", body=None, headers=None, timeout=30, base=None, context=None):
        data = body.encode() if isinstance(body, str) else body
        request = urllib.request.Request((base or self.base) + path, data=data, method=method, headers=headers or {})
        opener = _opener
        if context is not None:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}), _NoRedirects(), urllib.request.HTTPSHandler(context=context)
            )
        try:
            with opener.open(request, timeout=timeout) as response:
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


class Https(unittest.TestCase):
    """S34: plain HTTP is redirected and HSTS sent when HTTPS is on; the scheme comes only from trusted proxies."""

    def test_plain_http_is_redirected_except_lets_encrypt_checks(self):
        nginx = Nginx(NGINX_FORCE_HTTPS="true")
        response = nginx.request("/lessons/the-cell?lang=fr")
        self.assertEqual(response.status, 301)
        self.assertEqual(response.header("Location"), "https://127.0.0.1/lessons/the-cell?lang=fr")
        self.assertEqual(nginx.request("/api/meta/").status, 301)
        self.assertIsNone(response.header("Strict-Transport-Security"))  # never over plain HTTP
        self.assertEqual(nginx.request("/.well-known/acme-challenge/token").status, 404)  # served, not redirected

    def test_a_client_claiming_https_is_not_believed(self):
        nginx = Nginx(NGINX_FORCE_HTTPS="true")
        self.assertEqual(nginx.request("/", headers={"X-Forwarded-Proto": "https"}).status, 301)
        relaxed = Nginx(NGINX_FORCE_HTTPS="false")
        seen = relaxed.request("/api/meta/", headers={"X-Forwarded-Proto": "https"}).json()["headers"]
        self.assertEqual(seen["x-forwarded-proto"], "http")

    def test_behind_a_trusted_proxy_that_terminated_tls(self):
        nginx = Nginx(NGINX_FORCE_HTTPS="true", NGINX_TRUSTED_PROXIES=SUBNET)
        page = nginx.request("/", headers={"X-Forwarded-Proto": "https"})
        self.assertEqual(page.status, 200)
        self.assertEqual(page.header("Strict-Transport-Security"), "max-age=31536000; includeSubDomains")
        seen = nginx.request("/api/meta/", headers={"X-Forwarded-Proto": "https"}).json()["headers"]
        self.assertEqual(seen["x-forwarded-proto"], "https")  # so Django doesn't redirect in a loop
        self.assertEqual(nginx.request("/", headers={"X-Forwarded-Proto": "http"}).status, 301)

    def test_preload_only_when_asked(self):
        nginx = Nginx(NGINX_FORCE_HTTPS="true", NGINX_HSTS_PRELOAD="true", NGINX_TRUSTED_PROXIES=SUBNET)
        page = nginx.request("/", headers={"X-Forwarded-Proto": "https"})
        self.assertEqual(page.header("Strict-Transport-Security"), "max-age=31536000; includeSubDomains; preload")

    def test_the_local_trial_over_http(self):
        nginx = Nginx(NGINX_FORCE_HTTPS="false")
        page = nginx.request("/")
        self.assertEqual(page.status, 200)
        self.assertIsNone(page.header("Strict-Transport-Security"))

    def test_nginx_serves_https_itself_with_the_example_tls_conf(self):
        tls = tempfile.mkdtemp(prefix="iga-nginx-tls-")
        try:
            os.makedirs(os.path.join(tls, "conf"))
            os.makedirs(os.path.join(tls, "certs"))
            shutil.copy(os.path.join(FRONTEND, "nginx", "tls.conf.example"), os.path.join(tls, "conf", "tls.conf"))
            certs = os.path.join(tls, "certs")
            subprocess.run(
                ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=localhost",
                 "-addext", "subjectAltName=IP:127.0.0.1,DNS:localhost",
                 "-keyout", os.path.join(certs, "privkey.pem"), "-out", os.path.join(certs, "fullchain.pem")],
                check=True, capture_output=True,
            )  # fmt: skip
            for root, dirs, names in os.walk(tls):
                for name in dirs:
                    os.chmod(os.path.join(root, name), 0o755)
                for name in names:
                    os.chmod(os.path.join(root, name), 0o644)
            os.chmod(tls, 0o755)
            nginx = Nginx(
                extra_args=[
                    "-p",
                    "127.0.0.1::443",
                    "-v",
                    f"{tls}/conf:/etc/nginx/iga/tls:ro",
                    "-v",
                    f"{certs}:/etc/nginx/certs:ro",
                ],
                NGINX_FORCE_HTTPS="true",
            )
            https_port = docker("port", nginx.id, "443/tcp").splitlines()[0].rsplit(":", 1)[1]
            context = ssl.create_default_context(cafile=os.path.join(certs, "fullchain.pem"))
            page = nginx.request("/", base=f"https://127.0.0.1:{https_port}", context=context)
            self.assertEqual(page.status, 200)
            self.assertEqual(page.header("Strict-Transport-Security"), "max-age=31536000; includeSubDomains")
            seen = nginx.request("/api/meta/", base=f"https://127.0.0.1:{https_port}", context=context).json()
            self.assertEqual(seen["headers"]["x-forwarded-proto"], "https")
            self.assertEqual(nginx.request("/").status, 301)  # port 80 sends browsers to HTTPS
            # Old protocols are refused.
            old = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            old.load_verify_locations(os.path.join(certs, "fullchain.pem"))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                old.minimum_version = ssl.TLSVersion.TLSv1
                old.maximum_version = ssl.TLSVersion.TLSv1_1
            with self.assertRaises((ssl.SSLError, ConnectionError, urllib.error.URLError)):
                nginx.request("/", base=f"https://127.0.0.1:{https_port}", context=old)
        finally:
            shutil.rmtree(tls, ignore_errors=True)


class SecurityHeaders(unittest.TestCase):
    """S41: the app's pages and files carry a strict Content-Security-Policy and the other security headers."""

    @classmethod
    def setUpClass(cls):
        cls.nginx = Nginx(**LOW_LIMITS)

    def test_the_app_and_its_files_have_the_policy(self):
        for path in [
            "/",
            "/lessons/the-cell",
            "/assets/app-1234.js",
            "/assets/pyodide.worker-1234.js",
            "/pyodide/pyodide.mjs",
            "/sw.js",
        ]:
            response = self.nginx.request(path)
            self.assertEqual(response.status, 200, path)
            policy = response.header("Content-Security-Policy")
            directives = dict(d.strip().split(" ", 1) for d in policy.split(";") if " " in d.strip())
            self.assertEqual(directives["default-src"], "'self'", path)
            # Scripts: this site, WebAssembly compilation for Python/SQL, and GeoGebra's loader; never inline or eval.
            self.assertEqual(
                directives["script-src"], "'self' 'wasm-unsafe-eval' https://www.geogebra.org https://cdn.geogebra.org", path
            )
            self.assertEqual(directives["frame-src"], "'self' https://phet.colorado.edu https://www.geogebra.org", path)
            self.assertEqual(directives["frame-ancestors"], "'none'", path)
            self.assertEqual(directives["object-src"], "'none'", path)
            self.assertEqual(directives["base-uri"], "'self'", path)
            self.assertEqual(directives["form-action"], "'self'", path)
            self.assertEqual(directives["connect-src"].split()[0], "'self'", path)
            for name, value in {
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Resource-Policy": "same-origin",
            }.items():
                self.assertEqual(response.header(name), value, f"{path} {name}")
            self.assertIn("camera=()", response.header("Permissions-Policy"), path)

    def test_the_playground_preview_has_its_own_sandboxed_policy(self):
        response = self.nginx.request("/playground-frame.html")
        policy = response.header("Content-Security-Policy")
        self.assertTrue(policy.startswith("sandbox allow-scripts allow-modals;"), policy)
        self.assertIn("frame-ancestors 'self'", policy)
        self.assertEqual(response.header("X-Frame-Options"), "SAMEORIGIN")

    def test_nginx_refusals_have_headers_too(self):
        refused = None
        for _ in range(10):
            refused = self.nginx.post_json("/api/auth/login/")
        self.assertEqual(refused.status, 429)
        self.assertEqual(refused.header("Content-Security-Policy"), "default-src 'none'; frame-ancestors 'none'")
        self.assertEqual(refused.header("X-Frame-Options"), "DENY")
        too_large = self.nginx.request("/api/lessons/", "POST", b"x" * (3 * 1024 * 1024))
        self.assertEqual(too_large.header("Content-Security-Policy"), "default-src 'none'; frame-ancestors 'none'")

    def test_django_sets_its_own_on_the_api(self):
        # nginx adds none of its own to Django's answers (Django sends a stricter policy for JSON).
        response = self.nginx.request("/api/meta/")
        self.assertIsNone(response.header("Content-Security-Policy"))
        self.assertIsNone(response.header("X-Frame-Options"))

    def test_the_policy_can_be_replaced(self):
        nginx = Nginx(NGINX_CSP="default-src 'self'; frame-ancestors 'none'")
        self.assertEqual(nginx.request("/").header("Content-Security-Policy"), "default-src 'self'; frame-ancestors 'none'")


def _all_logs(container):
    result = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
    return result.stdout + result.stderr


if __name__ == "__main__":
    unittest.main(verbosity=2)
