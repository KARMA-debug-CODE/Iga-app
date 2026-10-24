"""The costly routes, Santa (its model) and the code runner, are out of reach for anyone who may not use them.

These tests sign in the real way (a Bearer token checked by IgaJWTAuthentication, not force_authenticate), so the
session checks run: anonymous visitors, deactivated accounts, ended sessions and accounts that must first replace
a teacher's temporary password get nothing, and Santa also needs a subscribed school. The fake model server and
the fake code runner record every call, so the tests also prove that nothing reached them."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.stepup import fresh_access_token

from .conftest import make_school, make_user
from .test_coderun import runner  # noqa: F401 - fixture
from .test_tutor import santa  # noqa: F401 - fixture

pytestmark = pytest.mark.django_db

SANTA = [("post", "/api/tutor/ask/"), ("post", "/api/tutor/stream/"), ("get", "/api/tutor/status/")]
RUNNER = [("post", "/api/code/run/"), ("post", "/api/code/input/"), ("post", "/api/code/stop/"), ("get", "/api/code/status/")]
BODY = {"message": "What is a cell?", "language": "cpp", "code": "int main(){}", "session": "s1", "text": "x"}


def signed_in(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {fresh_access_token(user)}")
    return client


def call(client, method, path):
    return getattr(client, method)(path, BODY if method == "post" else None, format="json")


@pytest.fixture
def backends(santa, runner):  # noqa: F811
    return santa, runner


def nothing_reached(backends):
    model, code_runner = backends
    return not [c for c in model.calls if c["path"].startswith("/v1/")] and not code_runner.calls


@pytest.mark.parametrize("method,path", SANTA + RUNNER)
def test_anonymous_visitors_get_nothing(backends, method, path):
    assert call(APIClient(), method, path).status_code == 401
    bad = APIClient()
    bad.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")
    assert call(bad, method, path).status_code == 401
    assert nothing_reached(backends)


@pytest.mark.parametrize("method,path", SANTA + RUNNER)
def test_deactivated_accounts_and_ended_sessions_get_nothing(backends, method, path):
    gone = make_user("gone")
    client = signed_in(gone)
    gone.is_active = False
    gone.save(update_fields=["is_active"])
    assert call(client, method, path).status_code == 401
    ended = make_user("ended")
    client = signed_in(ended)
    ended.bump_session_version()  # "log out everywhere", a password change...
    assert call(client, method, path).status_code == 401
    assert nothing_reached(backends)


@pytest.mark.parametrize("method,path", SANTA + RUNNER)
def test_a_temporary_password_must_be_replaced_first(backends, method, path):
    user = make_user("newcomer", must_change_password=True)
    response = call(signed_in(user), method, path)
    assert response.status_code == 403 and response.data["detail"].code == "password_change_required"
    assert nothing_reached(backends)


@pytest.mark.parametrize("path", ["/api/tutor/ask/", "/api/tutor/stream/"])
def test_santa_needs_a_subscribed_school(backends, path):
    lapsed = make_school("Lapsed", paid_until=timezone.now() - timedelta(days=30))  # past the grace days
    for user in (
        make_user("no-school", school=None),
        make_user("lapsed", school=lapsed),
        make_user("mum", role="parent"),
        make_user("pending-school", school=make_school("Pending")),  # never paid
    ):
        response = signed_in(user).post(path, BODY, format="json")
        assert response.status_code == 403 and response.data["detail"].code == "subscription_required", user
        assert signed_in(user).get("/api/tutor/status/").data["enabled"] is False
    assert nothing_reached(backends)


def test_a_subscribed_student_reaches_both(backends):
    student = make_user("pupil")
    client = signed_in(student)
    assert client.post("/api/tutor/ask/", BODY, format="json").status_code == 200
    assert client.post("/api/code/run/", BODY, format="json").status_code == 200
    model, code_runner = backends
    assert [c for c in model.calls if c["path"].startswith("/v1/")] and code_runner.calls
