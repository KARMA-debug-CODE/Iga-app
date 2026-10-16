"""Every API view is rate limited, signed in or not, and a made-up X-Forwarded-For header can't get around it.

nginx adds a second layer of per-IP limits in front of Django (frontend/nginx.conf); these tests cover the
Django layer, which also protects a deployment without the bundled nginx.
"""

import pytest
from django.test import RequestFactory
from rest_framework import throttling
from rest_framework.request import Request
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.core.throttles import AnonRateThrottle, UserRateThrottle

from .conftest import RELAXED_RATES
from .routes import api_routes, view_class, view_methods

pytestmark = pytest.mark.django_db


def limit(monkeypatch, **rates):
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RELAXED_RATES, **rates})


def _views(callback):
    """One view instance per HTTP method a route answers, set up as DRF would for that request."""
    cls = view_class(callback)
    actions = getattr(callback, "actions", None) or {}
    initkwargs = getattr(callback, "initkwargs", None) or {}
    for method in view_methods(callback):
        view = cls(**initkwargs)
        view.action = actions.get(method.lower())
        view.request = Request(RequestFactory().generic(method, "/"))
        view.args, view.kwargs, view.format_kwarg = (), {}, None
        yield method, view


def _applies(throttle, view):
    """A ScopedRateThrottle does nothing on a view without a throttle_scope; every other throttle counts."""
    if isinstance(throttle, throttling.ScopedRateThrottle):
        return bool(getattr(view, "throttle_scope", None))
    return True


def test_every_api_view_is_rate_limited():
    unlimited, emptied = [], []
    for route, callback in api_routes():
        if view_class(callback) is None:
            continue
        for method, view in _views(callback):
            if not view.throttle_classes:
                emptied.append(f"{method} /{route}")
            throttles = view.get_throttles()
            if not any(_applies(throttle, view) for throttle in throttles):
                unlimited.append(f"{method} /{route}")
            # Visitors who are not signed in are always limited by IP, signed-in users by account or IP.
            kinds = {type(throttle) for throttle in throttles}
            if kinds & {AnonRateThrottle, UserRateThrottle} and not kinds >= {AnonRateThrottle, UserRateThrottle}:
                unlimited.append(f"{method} /{route} (only one of the anon/user limits)")
    assert not emptied, f"Views with throttle_classes = []: {emptied}"
    assert not unlimited, f"Views with no rate limit: {unlimited}"


def test_anonymous_requests_are_limited_per_ip(monkeypatch, db):
    limit(monkeypatch, anon="3/min")
    client = APIClient()
    for _ in range(3):
        assert client.get("/api/meta/").status_code == 200
    response = client.get("/api/meta/")
    assert response.status_code == 429
    assert "detail" in response.json()
    assert int(response["Retry-After"]) > 0
    # Another address is not affected.
    assert APIClient(REMOTE_ADDR="10.9.9.9").get("/api/meta/").status_code == 200


def test_signed_in_requests_are_limited_per_user(monkeypatch, student, other_student, client_for):
    limit(monkeypatch, user="3/min")
    client = client_for(student)
    for _ in range(3):
        assert client.get("/api/dashboard/").status_code == 200
    assert client.get("/api/dashboard/").status_code == 429
    assert client_for(other_student).get("/api/dashboard/").status_code == 200


@pytest.mark.parametrize("hops", [0, 1])
def test_a_made_up_forwarded_for_header_does_not_reset_the_limit(monkeypatch, settings, hops):
    """Each request claims to come from a new address. Directly (0 proxies) the header is ignored; behind
    nginx (1 proxy) only the address nginx itself appended, the last one, counts."""
    settings.TRUSTED_PROXY_COUNT = hops
    limit(monkeypatch, anon="3/min")
    real = "41.186.1.9"

    def spoofed(i):
        forwarded = f"203.0.113.{i}" if hops == 0 else f"203.0.113.{i}, {real}"
        return APIClient(REMOTE_ADDR="10.0.0.2" if hops else real, HTTP_X_FORWARDED_FOR=forwarded)

    statuses = [spoofed(i).get("/api/meta/").status_code for i in range(5)]
    assert statuses == [200, 200, 200, 429, 429]


def test_a_made_up_forwarded_for_header_does_not_reset_the_sign_in_limit(monkeypatch, settings, student):
    settings.TRUSTED_PROXY_COUNT = 1
    limit(monkeypatch, auth="3/min")
    statuses = []
    for i in range(5):
        client = APIClient(REMOTE_ADDR="10.0.0.2", HTTP_X_FORWARDED_FOR=f"198.51.100.{i}, 41.186.1.9")
        response = client.post("/api/auth/login/", {"identifier": f"nobody{i}", "password": "wrong-password"}, format="json")
        statuses.append(response.status_code)
    assert statuses == [401, 401, 401, 429, 429]


def test_throttled_requests_are_security_events(monkeypatch, db):
    from apps.core.models import AuditLog

    limit(monkeypatch, anon="1/min")
    client = APIClient()
    client.get("/api/meta/")
    assert client.get("/api/meta/").status_code == 429
    assert AuditLog.objects.filter(action="throttled").exists()
