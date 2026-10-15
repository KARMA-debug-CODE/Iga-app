"""Role checks and step-up for privileged operations.

Privileged operations need the right role AND a password confirmed recently (sign-in or step-up), and
they are audit-logged. A lower role never reaches them, whatever its token says.
"""

import time

import pyotp
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import User
from apps.accounts.stepup import stamp
from apps.classroom.models import Classroom, Enrollment
from apps.core.models import AuditLog
from apps.core.permissions import IsPlatformAdmin, IsSchoolAdmin, IsTeacher, RecentAuthentication

from .conftest import make_school, make_user
from .routes import api_routes, fill, view_class, view_methods

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"
STEP_UP = "step_up_required"

# School administrators' privileged operations (membership decisions and billing), all POSTs.
SCHOOL_ADMIN_PRIVILEGED = [
    "/api/school/members/decide/",
    "/api/school/members/{user}/remove/",
    "/api/school/new-code/",
    "/api/billing/checkout/",
]


def admin_routes():
    return [(route, callback) for route, callback in api_routes() if route.startswith("api/admin/")]


def _permission_classes(callback):
    cls = view_class(callback)
    classes = set(cls.permission_classes)
    for action in (getattr(callback, "actions", None) or {}).values():
        override = getattr(getattr(cls, action, None), "kwargs", {}).get("permission_classes")
        if override is not None:
            classes &= set(override)
    return classes


@pytest.fixture
def world(db):
    school = make_school("Lycee", "Gasabo")
    return {
        "student": make_user("rbac_student"),
        "teacher": make_user("rbac_teacher", role=User.Role.TEACHER, teacher_approved=True),
        "parent": make_user("rbac_parent", role=User.Role.PARENT),
        "school_admin": make_user("rbac_school_admin", role=User.Role.SCHOOL_ADMIN, school=school),
        "admin": make_user("rbac_admin", role=User.Role.ADMIN),
        "school": school,
    }


def test_admin_routes_declare_admin_role_and_step_up():
    routes = admin_routes()
    assert len(routes) >= 12  # users, review, moderation, stats, audit, schools...
    for route, callback in routes:
        classes = _permission_classes(callback)
        assert IsPlatformAdmin in classes and RecentAuthentication in classes, route


def test_lower_roles_never_reach_admin_routes_even_freshly_signed_in(client_for, world):
    for role in ("student", "teacher", "parent", "school_admin"):
        client = client_for(world[role])
        for route, callback in admin_routes():
            url = fill(route, default=world["school"].id)
            for method in view_methods(callback):
                response = getattr(client, method.lower())(url, {}, format="json")
                assert response.status_code == 403, (role, method, url, response.status_code)
                assert response.data.get("code") != STEP_UP, (role, url)  # told "no", not asked for a password


def test_admins_must_step_up_after_the_sign_in_window(client_for, world):
    stale = client_for(world["admin"], signed_in=False)
    for route, callback in admin_routes():
        url = fill(route, default=world["school"].id)
        for method in view_methods(callback):
            response = getattr(stale, method.lower())(url, {}, format="json")
            assert response.status_code == 403, (method, url)
            assert response.data["code"] == STEP_UP, (method, url)
    fresh = client_for(world["admin"])
    assert fresh.get("/api/admin/stats/").status_code == 200
    assert fresh.get("/api/admin/users/").status_code == 200


def test_school_admin_privileged_operations(client_for, world):
    member = make_user("rbac_member", school=world["school"])
    for role in ("student", "teacher", "parent"):
        client = client_for(world[role])
        for url in SCHOOL_ADMIN_PRIVILEGED:
            response = client.post(url.format(user=member.id), {}, format="json")
            assert response.status_code == 403 and response.data.get("code") != STEP_UP, (role, url)
    stale = client_for(world["school_admin"], signed_in=False)
    for url in SCHOOL_ADMIN_PRIVILEGED:
        response = stale.post(url.format(user=member.id), {"ids": [member.id], "approve": True}, format="json")
        assert response.status_code == 403 and response.data["code"] == STEP_UP, url
    member.refresh_from_db()
    assert member.school_id == world["school"].id  # nothing happened
    fresh = client_for(world["school_admin"])
    assert fresh.post(f"/api/school/members/{member.id}/remove/").status_code == 204


def test_school_admin_routes_declare_the_role():
    by_route = dict(api_routes())
    for route in (
        "api/school/members/decide/",
        "api/school/members/{user_id}/remove/",
        "api/school/new-code/",
        "api/billing/checkout/",
    ):
        classes = _permission_classes(by_route[route])
        assert IsSchoolAdmin in classes and RecentAuthentication in classes, route
    for route in ("api/school/", "api/school/members/", "api/school/payments/"):
        assert IsSchoolAdmin in _permission_classes(by_route[route]), route


def test_resetting_a_students_password_needs_step_up_and_is_audited(client_for, world):
    teacher, student = world["teacher"], world["student"]
    classroom = Classroom.objects.create(name="S2 A", grade="S2", teacher=teacher)
    Enrollment.objects.create(classroom=classroom, student=student)
    url = f"/api/classes/{classroom.id}/reset_password/"
    stale = client_for(teacher, signed_in=False).post(url, {"student": student.id}, format="json")
    assert stale.status_code == 403 and stale.data["code"] == STEP_UP
    student.refresh_from_db()
    assert student.check_password(PASSWORD)
    assert client_for(student).post(url, {"student": student.id}, format="json").status_code == 403
    done = client_for(teacher).post(url, {"student": student.id}, format="json")
    assert done.status_code == 200
    assert AuditLog.objects.filter(action="reset_student_password", target_id=str(student.id), actor=teacher).exists()


def test_teacher_only_routes_refuse_other_roles(client_for, world):
    by_route = dict(api_routes())
    assert IsTeacher in _permission_classes(by_route["api/questions/"])
    assert IsTeacher in _permission_classes(by_route["api/marking/"])
    for role in ("student", "parent", "school_admin"):
        client = client_for(world[role])
        assert client.get("/api/questions/").status_code == 403, role
        assert client.get("/api/marking/").status_code == 403, role
        assert client.post("/api/classes/", {"name": "x", "grade": "S2"}, format="json").status_code == 403, role
    unapproved = make_user("rbac_pending_teacher", role=User.Role.TEACHER)
    assert client_for(unapproved).get("/api/questions/").status_code == 403


# --- The step-up endpoint and real tokens -------------------------------------------------------


def _login(username):
    client = APIClient()
    response = client.post("/api/auth/login/", {"identifier": username, "password": PASSWORD}, format="json")
    assert response.status_code == 200
    return client, response.data["access"]


def _bearer(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def test_the_sign_in_time_survives_a_refresh_but_is_never_renewed_by_one(world, settings):
    client, access = _login("rbac_admin")
    assert _bearer(access).get("/api/admin/stats/").status_code == 200
    # Reloading the page refreshes the session: still the same sign-in, still recent.
    refreshed = client.post("/api/auth/refresh/").data["access"]
    assert _bearer(refreshed).get("/api/admin/stats/").status_code == 200
    # A session signed in long ago stays "long ago" however often it is refreshed.
    old = RefreshToken.for_user(world["admin"])
    old["auth_time"] = int(time.time()) - settings.STEP_UP_MAX_AGE_SECONDS - 60
    stale = APIClient()
    stale.cookies["iga_refresh"] = str(old)
    response = _bearer(stale.post("/api/auth/refresh/").data["access"]).get("/api/admin/stats/")
    assert response.status_code == 403 and response.data["code"] == STEP_UP
    # A refresh token from before step-up existed (no sign-in time) gives no privileges either.
    legacy = APIClient()
    legacy.cookies["iga_refresh"] = str(RefreshToken.for_user(world["admin"]))
    response = _bearer(legacy.post("/api/auth/refresh/").data["access"]).get("/api/admin/stats/")
    assert response.status_code == 403 and response.data["code"] == STEP_UP


def test_step_up_with_the_password(world):
    admin = world["admin"]
    plain = str(AccessToken.for_user(admin))
    client = _bearer(plain)
    wrong = client.post("/api/auth/step-up/", {"password": "wrong-password"}, format="json")
    assert wrong.status_code == 400 and wrong.data["code"] == "step_up_failed"
    assert AuditLog.objects.filter(action="step_up_failed", actor=admin).exists()
    ok = client.post("/api/auth/step-up/", {"password": PASSWORD}, format="json")
    assert ok.status_code == 200
    assert AuditLog.objects.filter(action="step_up", actor=admin).exists()
    assert _bearer(ok.data["access"]).get("/api/admin/stats/").status_code == 200
    assert client_anonymous_step_up() == 401


def client_anonymous_step_up():
    return APIClient().post("/api/auth/step-up/", {"password": PASSWORD}, format="json").status_code


def test_step_up_asks_for_the_2fa_code_when_it_is_on(world):
    admin = world["admin"]
    admin.totp_secret = pyotp.random_base32()
    admin.totp_enabled = True
    admin.save()
    client = _bearer(str(AccessToken.for_user(admin)))
    no_code = client.post("/api/auth/step-up/", {"password": PASSWORD}, format="json")
    assert no_code.status_code == 400 and no_code.data["otp_required"]
    bad_code = client.post("/api/auth/step-up/", {"password": PASSWORD, "otp": "000000"}, format="json")
    assert bad_code.status_code == 400
    code = pyotp.TOTP(admin.totp_secret).now()
    assert client.post("/api/auth/step-up/", {"password": PASSWORD, "otp": code}, format="json").status_code == 200


def test_step_up_expires(world, settings):
    admin = world["admin"]
    token = stamp(AccessToken.for_user(admin))
    token["auth_time"] = int(time.time()) - settings.STEP_UP_MAX_AGE_SECONDS - 5
    response = _bearer(str(token)).get("/api/admin/stats/")
    assert response.status_code == 403 and response.data["code"] == STEP_UP
    token["auth_time"] = "yesterday"
    assert _bearer(str(token)).get("/api/admin/stats/").status_code == 403


def test_a_stamped_token_gives_no_extra_role(world):
    student_token = stamp(AccessToken.for_user(world["student"]))
    assert _bearer(str(student_token)).get("/api/admin/stats/").status_code == 403
    assert _bearer(str(student_token)).post("/api/school/new-code/").status_code == 403


def test_privileged_changes_are_audited(client_for, world):
    pending = make_user("rbac_pending", role=User.Role.TEACHER)
    client_for(world["admin"]).patch(f"/api/admin/users/{pending.id}/", {"teacher_approved": True}, format="json")
    assert AuditLog.objects.filter(action="update_user", target_id=str(pending.id)).exists()
    client_for(world["admin"]).get("/api/admin/users/", {"q": "rbac"})
    assert AuditLog.objects.filter(action="list_users", actor=world["admin"], details__q="rbac").exists()
    joiner = make_user("rbac_joiner", school=None)
    joiner.school = world["school"]
    joiner.school_status = User.SchoolStatus.PENDING
    joiner.save()
    client_for(world["school_admin"]).post("/api/school/members/decide/", {"ids": [joiner.id], "approve": True}, format="json")
    assert AuditLog.objects.filter(action="approve_members", actor=world["school_admin"]).exists()


# --- Step-up together with the sign-in protections (session versions, lockout) -------------------


def test_step_up_tokens_belong_to_the_current_session(world):
    """After a password change ends every other session, this device keeps its sign-in time, and a
    step-up token carries the new session version (or it would be refused as a token from an ended session)."""
    client, access = _login("rbac_admin")
    new_password = "N3w-str0ng-pass-456"
    changed = _bearer(access).post(
        "/api/auth/password/", {"current_password": PASSWORD, "new_password": new_password}, format="json"
    )
    assert changed.status_code == 200
    assert _bearer(access).get("/api/admin/stats/").status_code == 401  # the old session has ended
    assert _bearer(changed.data["access"]).get("/api/admin/stats/").status_code == 200  # same recent sign-in
    stepped = _bearer(changed.data["access"]).post("/api/auth/step-up/", {"password": new_password}, format="json")
    assert stepped.status_code == 200
    assert _bearer(stepped.data["access"]).get("/api/admin/stats/").status_code == 200
    # The cookie this device received keeps the sign-in time through a refresh too.
    client.cookies["iga_refresh"] = changed.cookies["iga_refresh"].value
    refreshed = client.post("/api/auth/refresh/").data["access"]
    assert _bearer(refreshed).get("/api/admin/stats/").status_code == 200


def test_wrong_step_up_passwords_lock_like_other_reauthentication(world, settings):
    settings.LOGIN_LOCKOUT_THRESHOLD = 3
    admin = world["admin"]
    client = _bearer(str(AccessToken.for_user(admin)))
    for _ in range(2):
        response = client.post("/api/auth/step-up/", {"password": "wrong-password"}, format="json")
        assert response.status_code == 400 and response.data["code"] == "step_up_failed"
    locked = client.post("/api/auth/step-up/", {"password": "wrong-password"}, format="json")
    assert locked.status_code == 429 and locked.data["retry_after"] > 0
    # Even the right password is refused while the lock lasts.
    again = client.post("/api/auth/step-up/", {"password": PASSWORD}, format="json")
    assert again.status_code == 429 and "access" not in again.data
    assert AuditLog.objects.filter(action="step_up_failed", actor=admin).count() >= 3
    assert AuditLog.objects.filter(action="account_locked", target_id=str(admin.pk)).exists()
    assert not AuditLog.objects.filter(action="step_up", actor=admin).exists()
