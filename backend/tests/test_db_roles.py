"""Least-privilege database roles (apps/core/dbroles.py, `manage.py db_roles`).

The PostgreSQL tests build a scratch database next to the test database the way an older single-role
deployment left it (tables owned by the superuser), run `manage.py db_roles` and then `manage.py migrate`
as the owner role, exactly as docker compose's "migrate" service does, start Iga as the app role, and
check, connected as each role, what it can and cannot do. They need PostgreSQL and a superuser test role
(CI has both); elsewhere they are skipped. The first tests need no database.
"""

import base64
import hashlib
import hmac
import os
import secrets
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from psycopg import sql

from apps.core.checks import database_role_check
from apps.core.dbroles import Role, RoleSetupError, role_from_url, scram_verifier, setup_roles

BACKEND = Path(__file__).resolve().parent.parent
postgresql_only = pytest.mark.skipif(connection.vendor != "postgresql", reason="needs PostgreSQL (CI runs it)")


# --- No database needed ----------------------------------------------------------------------------


def test_role_urls_are_checked():
    role = role_from_url("postgres://iga_app:a-long-app-password@db:5432/iga", "DB_APP_URL")
    assert role == Role(name="iga_app", password="a-long-app-password", database="iga")
    for url, message in [
        ("", "Set DB_APP_URL"),
        ("mysql://iga_app:a-long-app-password@db/iga", "postgres://"),
        ("nonsense", "not a database URL"),
        ("postgres://Iga-App:a-long-app-password@db/iga", "lowercase"),
        ('postgres://x";drop:a-long-app-password@db/iga', "lowercase"),
        ("postgres://iga_app:short@db/iga", "at least 12"),
        ("postgres://iga_app:mot-de-passe-%C3%A9t%C3%A9@db/iga", "plain ASCII"),
        ("postgres://iga_app@db/iga", "at least 12"),
    ]:
        with pytest.raises(RoleSetupError, match=message):
            role_from_url(url, "DB_APP_URL")


def test_well_known_passwords_are_refused_on_a_real_deployment(settings):
    settings.DEBUG, settings.HTTPS = False, False  # a local docker compose trial keeps them
    role_from_url("postgres://iga_app:iga-local-app@db/iga", "DB_APP_URL")
    settings.HTTPS = True
    for password in ("iga-local-app", "iga-local-owner"):
        with pytest.raises(RoleSetupError, match="well-known"):
            role_from_url(f"postgres://iga_app:{password}@db/iga", "DB_APP_URL")


def test_scram_verifier_follows_rfc_7677():
    """The worked example of RFC 7677: our stored and server keys must produce its server signature."""
    salt = base64.b64decode("W22ZaJ0SNY7soEsUEjb6gQ==")
    verifier = scram_verifier("pencil", salt=salt)
    method, rest = verifier.split("$", 1)
    params, keys = rest.split("$")
    stored_key, server_key = (base64.b64decode(part) for part in keys.split(":"))
    assert (method, params) == ("SCRAM-SHA-256", "4096:W22ZaJ0SNY7soEsUEjb6gQ==")
    nonce = "rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0"
    auth_message = f"n=user,r=rOprNGfwEbeRWgbNEkqO,r={nonce},s=W22ZaJ0SNY7soEsUEjb6gQ==,i=4096,c=biws,r={nonce}"
    signature = hmac.new(server_key, auth_message.encode(), hashlib.sha256).digest()
    assert base64.b64encode(signature).decode() == "6rriTRBi23WpRR/wtup+mMhUZUn/dB5nLTJRsjl95G4="
    proof = base64.b64decode("dHzbZapWIk4jUhN+Ute9ytag9zjfMHgsqmmiz7AndVQ=")
    client_signature = hmac.new(stored_key, auth_message.encode(), hashlib.sha256).digest()
    client_key = bytes(a ^ b for a, b in zip(proof, client_signature, strict=True))
    assert hashlib.sha256(client_key).digest() == stored_key
    assert scram_verifier("pencil") != scram_verifier("pencil")  # a fresh salt every time


@pytest.mark.skipif(connection.vendor == "postgresql", reason="checks the refusal on other databases")
def test_db_roles_needs_postgresql(monkeypatch):
    monkeypatch.setenv("DB_OWNER_URL", "postgres://iga_owner:a-long-owner-password@db/iga")
    monkeypatch.setenv("DB_APP_URL", "postgres://iga_app:a-long-app-password@db/iga")
    with pytest.raises(CommandError, match="only for PostgreSQL"):
        call_command("db_roles")


# --- On a real PostgreSQL server ---------------------------------------------------------------------


def _admin_params(dbname=None):
    settings = connection.settings_dict
    return {
        "host": settings["HOST"] or None,
        "port": settings["PORT"] or None,
        "user": settings["USER"],
        "password": settings["PASSWORD"],
        "dbname": dbname or settings["NAME"],
    }


def _url(user, password, dbname):
    settings = connection.settings_dict
    return f"postgres://{user}:{password}@{settings['HOST'] or 'localhost'}:{settings['PORT'] or 5432}/{dbname}"


class Scratch:
    """A scratch database with its own owner and app roles (random names, dropped afterwards)."""

    def __init__(self):
        suffix = secrets.token_hex(4)
        self.db = f"iga_roles_{suffix}"
        self.owner = Role(f"iga_owner_{suffix}", secrets.token_urlsafe(24), self.db)
        self.app = Role(f"iga_app_{suffix}", secrets.token_urlsafe(24), self.db)
        self.stranger = f"iga_stranger_{suffix}"
        settings = connection.settings_dict
        self.superuser_url = _url(settings["USER"], settings["PASSWORD"], self.db)

    def url(self, role):
        return _url(role.name, role.password, self.db)

    def connect(self, role, **kwargs):
        return psycopg.connect(**{**_admin_params(self.db), "user": role.name, "password": role.password}, **kwargs)

    def manage(self, *args, url, production=False):
        """manage.py in a fresh process, configured like the docker compose services."""
        env = {name: os.environ[name] for name in ("PATH", "HOME", "LANG", "TMPDIR") if name in os.environ}
        env.update(
            DJANGO_SETTINGS_MODULE="config.settings",
            DJANGO_SECRET_KEY="db-roles-test-secret-key-that-is-long-enough-0123456789",
            DJANGO_DEBUG="false",
            # Required with DEBUG off (encrypted fields): the key this test run uses, never one in the repository.
            FIELD_ENCRYPTION_KEYS=os.environ["FIELD_ENCRYPTION_KEYS"],
            HTTPS="true" if production else "false",
            SANTA_URL="",
            CODE_RUNNER_URL="",
            DATABASE_URL=url,
            DB_OWNER_URL=self.url(self.owner),
            DB_APP_URL=self.url(self.app),
        )
        return subprocess.run(
            [sys.executable, "manage.py", *args], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=600
        )


@pytest.fixture(scope="module")
def scratch():
    with psycopg.connect(**_admin_params(), autocommit=True) as admin:
        if not admin.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()[0]:
            pytest.skip("the test database role must be a superuser to set up roles")
        world = Scratch()
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(world.db)))
    try:
        # What an older single-role setup left: tables, id sequences, a standalone sequence and a view,
        # all owned by the superuser.
        with psycopg.connect(**_admin_params(world.db), autocommit=True) as legacy:
            legacy.execute("CREATE TABLE legacy_notes (id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, body text)")
            legacy.execute("CREATE TABLE legacy_serial (id serial PRIMARY KEY)")
            legacy.execute("CREATE SEQUENCE legacy_counter")
            legacy.execute("CREATE VIEW legacy_view AS SELECT id, body FROM legacy_notes")
        result = world.manage("db_roles", url=world.superuser_url)
        assert result.returncode == 0, result.stderr
        assert "4 moved" in result.stdout, result.stdout
        result = world.manage("migrate", "--noinput", url=world.url(world.owner), production=True)
        assert result.returncode == 0, result.stderr
        yield world
    finally:
        with psycopg.connect(**_admin_params(), autocommit=True) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                [world.db],
            )
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(world.db)))
            for name in (world.owner.name, world.app.name, world.stranger):
                admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(name)))


def _as_superuser(world, query, params=None):
    with psycopg.connect(**_admin_params(world.db), autocommit=True) as admin:
        return admin.execute(query, params).fetchall()


@postgresql_only
def test_neither_role_has_any_power(scratch):
    rows = _as_superuser(
        scratch,
        "SELECT rolname, rolcanlogin, rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls "
        "FROM pg_roles WHERE rolname = ANY(%s) ORDER BY rolname",
        [[scratch.owner.name, scratch.app.name]],
    )
    assert rows == sorted((name, True, False, False, False, False, False) for name in (scratch.owner.name, scratch.app.name))
    members = _as_superuser(
        scratch,
        "SELECT count(*) FROM pg_auth_members m JOIN pg_roles u ON u.oid = m.member WHERE u.rolname = ANY(%s)",
        [[scratch.owner.name, scratch.app.name]],
    )
    assert members == [(0,)]


@postgresql_only
def test_the_owner_owns_every_table_including_ones_left_by_a_single_role_setup(scratch):
    owners = dict(
        _as_superuser(
            scratch,
            "SELECT c.relname, pg_get_userbyid(c.relowner) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'v', 'S')",
        )
    )
    for name in ("legacy_notes", "legacy_notes_id_seq", "legacy_serial", "legacy_serial_id_seq", "legacy_counter", "legacy_view"):
        assert owners[name] == scratch.owner.name, name
    assert owners["accounts_user"] == owners["django_migrations"] == scratch.owner.name
    assert set(owners.values()) == {scratch.owner.name}


@postgresql_only
def test_iga_starts_and_works_as_the_app_role(scratch):
    # The backend container's start: migrate (nothing to apply, system checks in production mode) ...
    result = scratch.manage("migrate", "--noinput", url=scratch.url(scratch.app), production=True)
    assert result.returncode == 0, result.stderr
    assert "No migrations to apply" in result.stdout
    assert "iga.E004" not in result.stderr and "iga.W002" not in result.stderr
    # ... then real requests: sign-up rows, a sign-in (tokens, audit), a locked update and deletes.
    script = """
from django.db import transaction
from django.test import Client
from apps.accounts.models import User
from apps.schools.models import School

school = School.objects.create(name="Roles School", district="Gasabo")
user = User.objects.create_user(username="rolecheck", password="Str0ng-pass-123", email="rolecheck@example.com",
                                role="student", grade="S2", school=school)
response = Client().post("/api/auth/login/", {"identifier": "rolecheck", "password": "Str0ng-pass-123"},
                         content_type="application/json")
assert response.status_code == 200, response.content
with transaction.atomic():
    School.objects.select_for_update().get(pk=school.pk)
    School.objects.filter(pk=school.pk).update(phone="+250 788 000 000")
user.delete()
school.delete()
print("app role ok")
"""
    result = scratch.manage("shell", "-c", script, url=scratch.url(scratch.app))
    assert result.returncode == 0, result.stderr
    assert "app role ok" in result.stdout


@postgresql_only
def test_the_app_role_only_reads_and_writes_rows(scratch):
    forbidden = [
        "CREATE TABLE stolen (id int)",
        "DROP TABLE accounts_user",
        "ALTER TABLE accounts_user ADD COLUMN backdoor text",
        "ALTER TABLE accounts_user DISABLE TRIGGER ALL",
        "TRUNCATE django_content_type CASCADE",
        "CREATE INDEX evil ON accounts_user (username)",
        "CREATE TEMP TABLE scratchpad (id int)",
        "CREATE SCHEMA evil",
        "CREATE FUNCTION public.evil() RETURNS int AS 'SELECT 1' LANGUAGE sql",
        "CREATE ROLE evil",
        "CREATE DATABASE evil",
        f"ALTER ROLE {scratch.app.name} SUPERUSER",
        f"SET ROLE {scratch.owner.name}",
        "COPY (SELECT 1) TO PROGRAM 'id'",
        "COPY accounts_user TO '/tmp/users.csv'",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT rolpassword FROM pg_authid",
    ]
    with scratch.connect(scratch.app, autocommit=True) as app:
        for statement in forbidden:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                app.execute(statement)
        # Rows: yes, including the tables and sequences an older setup left.
        new_id = app.execute("INSERT INTO legacy_notes (body) VALUES ('note') RETURNING id").fetchone()[0]
        app.execute("INSERT INTO legacy_serial DEFAULT VALUES")
        app.execute("SELECT nextval('legacy_counter')")
        assert app.execute("SELECT body FROM legacy_view WHERE id = %s", [new_id]).fetchone() == ("note",)
        with app.transaction():
            app.execute("SELECT id FROM legacy_notes WHERE id = %s FOR UPDATE", [new_id])
            app.execute("UPDATE legacy_notes SET body = 'edited' WHERE id = %s", [new_id])
        app.execute("DELETE FROM legacy_notes WHERE id = %s", [new_id])
        # It can't pass its rights on either.
        grant_option = app.execute(
            "SELECT bool_or(has_table_privilege(current_user, c.oid, 'SELECT WITH GRANT OPTION')) FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relkind = 'r'"
        ).fetchone()[0]
        assert grant_option is False


@postgresql_only
def test_tables_from_later_migrations_reach_the_app_for_rows_only(scratch):
    with scratch.connect(scratch.owner, autocommit=True) as owner:
        owner.execute("CREATE TABLE later_feature (id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, label text)")
        for statement in (
            "CREATE ROLE evil",
            "CREATE DATABASE evil",
            "COPY (SELECT 1) TO PROGRAM 'id'",
            "SELECT * FROM pg_authid",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                owner.execute(statement)
    try:
        with scratch.connect(scratch.app, autocommit=True) as app:
            row_id = app.execute("INSERT INTO later_feature (label) VALUES ('new') RETURNING id").fetchone()[0]
            app.execute("UPDATE later_feature SET label = 'newer' WHERE id = %s", [row_id])
            assert app.execute("SELECT label FROM later_feature").fetchall() == [("newer",)]
            app.execute("DELETE FROM later_feature")
            for statement in ("DROP TABLE later_feature", "TRUNCATE later_feature", "ALTER TABLE later_feature ADD COLUMN x int"):
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    app.execute(statement)
    finally:
        with scratch.connect(scratch.owner, autocommit=True) as owner:
            owner.execute("DROP TABLE later_feature")


@postgresql_only
def test_no_other_role_may_connect(scratch):
    stranger = Role(scratch.stranger, secrets.token_urlsafe(24), scratch.db)
    with psycopg.connect(**_admin_params(), autocommit=True) as admin:
        admin.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(stranger.name), sql.Literal(stranger.password))
        )
    with pytest.raises(psycopg.OperationalError, match="permission denied for database"):
        scratch.connect(stranger).close()


@postgresql_only
def test_running_it_again_is_safe_and_rotates_passwords(scratch):
    old = scratch.app
    scratch.app = Role(old.name, secrets.token_urlsafe(24), scratch.db)
    try:
        result = scratch.manage("db_roles", url=scratch.superuser_url)
        assert result.returncode == 0, result.stderr
        assert "moved" not in result.stdout  # everything already belongs to the owner
        scratch.connect(scratch.app).close()
        with pytest.raises(psycopg.OperationalError, match="password authentication failed"):
            scratch.connect(old).close()
    finally:
        scratch.app = old
        assert scratch.manage("db_roles", url=scratch.superuser_url).returncode == 0
    scratch.connect(scratch.app).close()


@postgresql_only
@pytest.mark.django_db
def test_a_superuser_connection_fails_the_production_checks(settings):
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        superuser = cursor.fetchone()[0]
    settings.DEBUG, settings.HTTPS = False, False
    assert database_role_check(None, databases=["default"]) == []  # a local trial over plain http
    settings.HTTPS = True
    ids = [problem.id for problem in database_role_check(None, databases=["default"])]
    assert ids == (["iga.E004"] if superuser else [])
    assert database_role_check(None, databases=None) == []  # only when the database is checked (migrate)


@postgresql_only
@pytest.mark.django_db
def test_db_roles_never_touches_the_superuser_it_runs_as():
    name, database = connection.settings_dict["USER"], connection.settings_dict["NAME"]
    with pytest.raises(RoleSetupError, match="superuser this command connects as"):
        setup_roles(Role(name, secrets.token_urlsafe(24), database), Role("iga_app_never", secrets.token_urlsafe(24), database))
    with pytest.raises(RoleSetupError, match="two different roles"):
        setup_roles(Role("iga_same", "x" * 20, database), Role("iga_same", "y" * 20, database))
    with pytest.raises(RoleSetupError, match="names database"):
        setup_roles(Role("iga_owner_x", "x" * 20, "elsewhere"), Role("iga_app_x", "y" * 20, database))
