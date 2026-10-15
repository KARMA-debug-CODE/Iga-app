"""Least-privilege PostgreSQL roles: one owns the tables and runs the migrations, the other is all Django runs as.

The browser never talks to the database; every query comes from Django. So what a successful SQL injection
or a stolen app password could do is bounded by the role Django connects as. `manage.py db_roles` (run with
the superuser in DATABASE_URL; docker compose's "migrate" service does it before every start) sets up:

- the owner role (DB_OWNER_URL, iga_owner in docker compose): owns every table, view and sequence in the
  public schema and may create new ones. `manage.py migrate` runs as it, nothing else does.
- the app role (DB_APP_URL, iga_app; the running app's DATABASE_URL): may connect to this database and
  SELECT, INSERT, UPDATE and DELETE rows (and use the sequences behind ids), nothing more. It cannot
  create, alter, drop or truncate a table, create temporary tables, roles or databases, read server files
  or run programs, and it belongs to no other role. Tables that later migrations create get the same
  grants automatically (the owner's default privileges).

Neither role is a superuser or has CREATEDB, CREATEROLE, REPLICATION or BYPASSRLS, and other roles on the
server (PUBLIC) may not connect to the database at all. Running it again is safe: it re-applies all of this,
sets the passwords from the URLs (so changing them in .env rotates them), and moves tables left by an older
single-role setup to the owner. Passwords are sent as SCRAM-SHA-256 verifiers, never in clear text, so they
cannot end up in the server's logs.
"""

import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass

import dj_database_url
from django.db import connections, transaction
from psycopg import sql

from .checks import KNOWN_LOCAL_SECRETS, real_deployment

SCHEMA = "public"
ROLE_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
# Role attributes that give powers beyond reading and writing rows, as pg_roles columns.
POWERS = {
    "rolsuper": "superuser",
    "rolcreaterole": "createrole",
    "rolcreatedb": "createdb",
    "rolreplication": "replication",
    "rolbypassrls": "bypassrls",
}
MIN_PASSWORD_LENGTH = 12


class RoleSetupError(Exception):
    pass


@dataclass(frozen=True)
class Role:
    name: str
    password: str
    database: str


def role_from_url(url, setting):
    """The role name, password and database in a postgres:// URL (DB_OWNER_URL or DB_APP_URL)."""
    if not url:
        raise RoleSetupError(f"Set {setting} to postgres://<role>:<password>@<host>:<port>/<database>.")
    try:
        parsed = dj_database_url.parse(url)
    except ValueError as exc:
        raise RoleSetupError(f"{setting} is not a database URL: {exc}")
    if not parsed.get("ENGINE", "").endswith("postgresql"):
        raise RoleSetupError(f"{setting} must be a postgres:// URL.")
    name, password = parsed.get("USER") or "", parsed.get("PASSWORD") or ""
    if not ROLE_NAME.match(name):
        raise RoleSetupError(f"The role name in {setting} must be lowercase letters, digits and _ (at most 63).")
    if len(password) < MIN_PASSWORD_LENGTH or not all(" " <= char <= "~" for char in password):
        raise RoleSetupError(
            f"The password in {setting} must be at least {MIN_PASSWORD_LENGTH} characters of plain ASCII "
            '(for example the output of python -c "import secrets; print(secrets.token_urlsafe(32))").'
        )
    if real_deployment() and password in KNOWN_LOCAL_SECRETS:
        raise RoleSetupError(f"The password in {setting} is a well-known local value: set a long random one in .env.")
    return Role(name=name, password=password, database=parsed.get("NAME") or "")


def scram_verifier(password, iterations=4096, salt=None):
    """What PostgreSQL stores for a SCRAM-SHA-256 password (RFC 5802/7677), computed here like psql's
    \\password does, so the clear password never reaches the server or its statement log."""
    salt = salt or secrets.token_bytes(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()

    def b64(data):
        return base64.b64encode(data).decode()

    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(stored_key)}:{b64(server_key)}"


def current_role_powers(connection):
    """(role name, [powers]) for the role this connection uses."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls "
            "FROM pg_roles WHERE rolname = current_user"
        )
        name, *flags = cursor.fetchone()
    return name, [label for label, on in zip(POWERS.values(), flags, strict=True) if on]


def setup_roles(owner, app, using="default"):
    """Create or update the owner and app roles on the database `using` connects to (as a superuser)."""
    connection = connections[using]
    if connection.vendor != "postgresql":
        raise RoleSetupError("Database roles are only for PostgreSQL; DATABASE_URL points at another database.")
    database = connection.settings_dict["NAME"]
    if owner.name == app.name:
        raise RoleSetupError("DB_OWNER_URL and DB_APP_URL must use two different roles.")
    for role, setting in ((owner, "DB_OWNER_URL"), (app, "DB_APP_URL")):
        if role.database != database:
            raise RoleSetupError(f"{setting} names database {role.database!r}, but DATABASE_URL is {database!r}.")

    with transaction.atomic(using=using), connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        admin = cursor.fetchone()[0]
        for role in (owner, app):
            cursor.execute("SELECT oid = 10 FROM pg_roles WHERE rolname = %s", [role.name])
            existing = cursor.fetchone()
            if role.name == admin or (existing and existing[0]):
                raise RoleSetupError(f"{role.name} is the superuser this command connects as: choose another role name.")
            if not existing:
                cursor.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(role.name)))
            cursor.execute(
                sql.SQL(
                    "ALTER ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}"
                ).format(sql.Identifier(role.name), sql.Literal(scram_verifier(role.password)))
            )
            # No powers inherited from other roles (pg_read_server_files, the owner role, ...).
            cursor.execute(
                "SELECT g.rolname FROM pg_auth_members m JOIN pg_roles g ON g.oid = m.roleid "
                "JOIN pg_roles u ON u.oid = m.member WHERE u.rolname = %s",
                [role.name],
            )
            for (group,) in cursor.fetchall():
                cursor.execute(sql.SQL("REVOKE {} FROM {}").format(sql.Identifier(group), sql.Identifier(role.name)))

        # Only these two roles (and superusers) may connect; the owner may make temporary tables, the app not.
        cursor.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
        cursor.execute(
            sql.SQL("GRANT CONNECT, TEMPORARY ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(owner.name))
        )
        cursor.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM {}").format(sql.Identifier(database), sql.Identifier(app.name)))
        cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(app.name)))

        # Only the owner creates objects in the schema.
        cursor.execute(sql.SQL("REVOKE CREATE ON SCHEMA {} FROM PUBLIC").format(sql.Identifier(SCHEMA)))
        cursor.execute(
            sql.SQL("GRANT USAGE, CREATE ON SCHEMA {} TO {}").format(sql.Identifier(SCHEMA), sql.Identifier(owner.name))
        )
        cursor.execute(sql.SQL("REVOKE ALL ON SCHEMA {} FROM {}").format(sql.Identifier(SCHEMA), sql.Identifier(app.name)))
        cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(SCHEMA), sql.Identifier(app.name)))

        # Tables, views and sequences left by an older setup (one role for everything) move to the owner.
        # A table takes its id sequences with it; standalone sequences are moved after.
        moved = 0
        cursor.execute(
            "SELECT c.relname, c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = %s AND c.relkind IN ('r', 'p', 'v', 'm') AND pg_get_userbyid(c.relowner) <> %s "
            "AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype = 'e') ORDER BY c.relname",
            [SCHEMA, owner.name],
        )
        for name, kind in cursor.fetchall():
            if kind == "v":
                cursor.execute(
                    sql.SQL("ALTER VIEW {} OWNER TO {}").format(sql.Identifier(SCHEMA, name), sql.Identifier(owner.name))
                )
            elif kind == "m":
                cursor.execute(
                    sql.SQL("ALTER MATERIALIZED VIEW {} OWNER TO {}").format(
                        sql.Identifier(SCHEMA, name), sql.Identifier(owner.name)
                    )
                )
            else:
                cursor.execute(
                    sql.SQL("ALTER TABLE {} OWNER TO {}").format(sql.Identifier(SCHEMA, name), sql.Identifier(owner.name))
                )
            moved += 1
        cursor.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = %s AND c.relkind = 'S' AND pg_get_userbyid(c.relowner) <> %s "
            "AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype IN ('a', 'i', 'e')) "
            "ORDER BY c.relname",
            [SCHEMA, owner.name],
        )
        for (name,) in cursor.fetchall():
            cursor.execute(
                sql.SQL("ALTER SEQUENCE {} OWNER TO {}").format(sql.Identifier(SCHEMA, name), sql.Identifier(owner.name))
            )
            moved += 1

        # The app reads and writes rows, nothing else; other roles get nothing.
        cursor.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM PUBLIC").format(sql.Identifier(SCHEMA)))
        cursor.execute(
            sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM {}").format(sql.Identifier(SCHEMA), sql.Identifier(app.name))
        )
        cursor.execute(
            sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {} TO {}").format(
                sql.Identifier(SCHEMA), sql.Identifier(app.name)
            )
        )
        cursor.execute(sql.SQL("REVOKE ALL ON ALL SEQUENCES IN SCHEMA {} FROM PUBLIC").format(sql.Identifier(SCHEMA)))
        cursor.execute(
            sql.SQL("REVOKE ALL ON ALL SEQUENCES IN SCHEMA {} FROM {}").format(sql.Identifier(SCHEMA), sql.Identifier(app.name))
        )
        cursor.execute(
            sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {} TO {}").format(
                sql.Identifier(SCHEMA), sql.Identifier(app.name)
            )
        )
        # ... and the same on every table and sequence the owner creates later (new migrations).
        cursor.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA {} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
            ).format(sql.Identifier(owner.name), sql.Identifier(SCHEMA), sql.Identifier(app.name))
        )
        cursor.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA {} GRANT USAGE, SELECT ON SEQUENCES TO {}").format(
                sql.Identifier(owner.name), sql.Identifier(SCHEMA), sql.Identifier(app.name)
            )
        )

        problems = _problems(cursor, owner, app, database)
        if problems:
            raise RoleSetupError("The roles are not as expected: " + "; ".join(problems))
        cursor.execute(
            "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = %s AND c.relkind IN ('r', 'p')",
            [SCHEMA],
        )
        tables = cursor.fetchone()[0]
    return {"tables": tables, "moved": moved}


def _problems(cursor, owner, app, database):
    """Everything setup_roles promises, read back from the catalogue."""
    problems = []
    for role in (owner, app):
        cursor.execute(
            "SELECT rolcanlogin, rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls "
            "FROM pg_roles WHERE rolname = %s",
            [role.name],
        )
        can_login, *flags = cursor.fetchone()
        powers = [label for label, on in zip(POWERS.values(), flags, strict=True) if on]
        if not can_login or powers:
            problems.append(f"{role.name} has {', '.join(powers) or 'no login'}")
        cursor.execute(
            "SELECT count(*) FROM pg_auth_members m JOIN pg_roles u ON u.oid = m.member WHERE u.rolname = %s",
            [role.name],
        )
        if cursor.fetchone()[0]:
            problems.append(f"{role.name} is still a member of another role")
    cursor.execute(
        "SELECT has_database_privilege(%s, %s, 'CREATE'), has_database_privilege(%s, %s, 'TEMPORARY'), "
        "has_schema_privilege(%s, %s, 'CREATE')",
        [app.name, database, app.name, database, app.name, SCHEMA],
    )
    if any(cursor.fetchone()):
        problems.append(f"{app.name} may create objects")
    cursor.execute(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = %s AND c.relkind IN ('r', 'p', 'v', 'm', 'S') AND pg_get_userbyid(c.relowner) <> %s "
        "AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype = 'e')",
        [SCHEMA, owner.name],
    )
    others = [name for (name,) in cursor.fetchall()]
    if others:
        problems.append(f"not owned by {owner.name}: {', '.join(sorted(others)[:10])}")
    return problems
