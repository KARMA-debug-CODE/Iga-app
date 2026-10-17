"""Argon2id password hashing, upgrading older hashes, and password rules (S37)."""

import pytest
from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient

from apps.accounts.models import User

from .conftest import make_user

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"


def test_new_passwords_are_hashed_with_argon2id(client_for):
    response = client_for().post(
        "/api/auth/register/",
        {"username": "newkid", "password": PASSWORD, "first_name": "New", "grade": "S1", "accept_terms": True},
        format="json",
    )
    assert response.status_code == 201
    assert User.objects.get(username="newkid").password.startswith("argon2$argon2id$")


def test_older_pbkdf2_hashes_still_work_and_are_upgraded_at_login(db):
    user = make_user("oldtimer")
    User.objects.filter(pk=user.pk).update(password=make_password(PASSWORD, hasher="pbkdf2_sha256"))
    assert User.objects.get(pk=user.pk).password.startswith("pbkdf2_sha256$")

    response = APIClient().post("/api/auth/login/", {"identifier": "oldtimer", "password": PASSWORD}, format="json")
    assert response.status_code == 200
    upgraded = User.objects.get(pk=user.pk).password
    assert upgraded.startswith("argon2$argon2id$")
    # The upgrade keeps the same password, and the user's sessions.
    again = APIClient().post("/api/auth/login/", {"identifier": "oldtimer", "password": PASSWORD}, format="json")
    assert again.status_code == 200


def test_changed_argon2_costs_rehash_at_next_login(db, settings):
    user = make_user("tuned")
    before = User.objects.get(pk=user.pk).password
    settings.ARGON2_TIME_COST = 3
    response = APIClient().post("/api/auth/login/", {"identifier": "tuned", "password": PASSWORD}, format="json")
    assert response.status_code == 200
    after = User.objects.get(pk=user.pk).password
    assert after != before and ",t=3," in after


@pytest.mark.parametrize("weak", ["qwertyuiop", "password123", "12345678901", "short1!"])
def test_common_numeric_and_short_passwords_are_refused(client_for, weak):
    response = client_for().post(
        "/api/auth/register/",
        {"username": "weakling", "password": weak, "first_name": "Weak", "grade": "S1", "accept_terms": True},
        format="json",
    )
    assert response.status_code == 400
    assert not User.objects.filter(username="weakling").exists()


def test_password_similar_to_the_username_is_refused(client_for):
    response = client_for().post(
        "/api/auth/register/",
        {"username": "uwimanaaline", "password": "uwimanaaline1", "first_name": "Aline", "grade": "S1", "accept_terms": True},
        format="json",
    )
    assert response.status_code == 400
