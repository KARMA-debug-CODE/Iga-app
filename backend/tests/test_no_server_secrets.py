"""No server secret ever reaches the browser.

Iga's browser only calls the API; Django holds the database credentials and every other key, and makes
every query itself (there is no "public" database key to hand out). This walks every API route, plus the
pages Django serves outside /api/, as every role, and checks that no answer (body or headers) contains the
database password or URL, Django's secret key, the field encryption keys or an internal service's key. The
frontend side is frontend/src/no-server-secrets.test.js.
"""

import pytest
from django.conf import settings as django_settings

from apps.accounts.models import User

from .conftest import make_school, make_user
from .routes import api_routes, fill, view_methods

pytestmark = pytest.mark.django_db

MARKERS = {
    "SANTA_API_KEY": "santa-key-marker-7d1f0c",
    "CODE_RUNNER_TOKEN": "runner-token-marker-93ab2e",
    "FLUTTERWAVE_SECRET_KEY": "FLWSECK-marker-5e8c41",
    "FLUTTERWAVE_WEBHOOK_HASH": "webhook-hash-marker-c02d77",
}
OTHER_PAGES = ["/", "/health/", "/api/", "/api/no-such-route/", "/django-admin/", "/admin/", "/static/../config/settings.py"]


def _secrets():
    found = dict(MARKERS)
    found["SECRET_KEY"] = django_settings.SECRET_KEY
    for n, key in enumerate(django_settings.FIELD_ENCRYPTION_KEYS):  # encrypts 2FA secrets and personal data
        found[f"FIELD_ENCRYPTION_KEYS[{n}]"] = key
    database = django_settings.DATABASES["default"]
    if len(database.get("PASSWORD") or "") >= 6:  # CI's throwaway "iga" is too common a word to look for
        found["database password"] = database["PASSWORD"]
    found["database URL"] = "postgres://"
    found["DATABASE_URL"] = "DATABASE_URL"
    return found


def test_no_answer_carries_a_server_secret(client_for, settings):
    for name, value in MARKERS.items():
        setattr(settings, name, value)
    school = make_school("Lycee", "Gasabo")
    people = {
        "anonymous": None,
        "student": make_user("secretstudent"),
        "teacher": make_user("secretteacher", role=User.Role.TEACHER, teacher_approved=True),
        "parent": make_user("secretparent", role=User.Role.PARENT),
        "school_admin": make_user("secretschooladmin", role=User.Role.SCHOOL_ADMIN, school=school),
        "admin": make_user("secretadmin", role=User.Role.ADMIN),
    }
    secrets = _secrets()
    leaks = []
    for role, user in people.items():
        client = client_for(user)
        client.raise_request_exception = False
        urls = [fill(route) for route, callback in api_routes() if "GET" in view_methods(callback)] + OTHER_PAGES
        for url in urls:
            response = client.get(url)
            text = response.content.decode("utf-8", "replace") + " ".join(f"{k}: {v}" for k, v in response.items())
            leaks += [(role, url, what) for what, value in secrets.items() if value and value in text]
    assert not leaks, leaks
