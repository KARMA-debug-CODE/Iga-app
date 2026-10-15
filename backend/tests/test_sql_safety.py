"""Every database query is parameterised: no SQL is ever built from strings.

All data access goes through the Django ORM, which sends values as query parameters. This test reads
the source of every app and fails on any raw SQL whose text is not a fixed string literal, so a value
can never be pasted into a query (the app's only raw SQL is the health check's constant "SELECT 1"; the
system checks and `manage.py db_roles` read the catalogue with constant queries and parameters).

Statements that cannot take parameters (CREATE ROLE, GRANT, ALTER ... OWNER TO: names are not values)
may use psycopg's composition, sql.SQL("<fixed text>").format(...), where every name or value is wrapped
in sql.Identifier(...) or sql.Literal(...), which quote them. Anything else is refused.
"""

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
SOURCES = [BACKEND / "apps", BACKEND / "config", BACKEND / "scripts"]
RAW_CALLS = {"raw", "extra", "execute", "executemany", "RawSQL"}


def _calls():
    for root in SOURCES:
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
                    if name in RAW_CALLS:
                        yield path.relative_to(BACKEND), node, name


def _is_text(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_quoted(node):
    """sql.Identifier(...) or sql.Literal(...): psycopg quotes whatever they wrap."""
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"Identifier", "Literal"}


def _is_composed(node):
    """sql.SQL("<fixed text>").format(<only quoted names and values>)."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format"):
        return False
    template = node.func.value
    if not (
        isinstance(template, ast.Call)
        and isinstance(template.func, ast.Attribute)
        and template.func.attr == "SQL"
        and len(template.args) == 1
        and _is_text(template.args[0])
    ):
        return False
    return all(_is_quoted(arg) for arg in [*node.args, *(keyword.value for keyword in node.keywords)])


def test_raw_sql_is_only_ever_a_constant_with_parameters():
    unsafe = []
    for path, node, name in _calls():
        if name == "extra":
            unsafe.append(f"{path}:{node.lineno} .extra() (use the ORM)")
            continue
        sql = node.args[0] if node.args else None
        if not (_is_text(sql) or (name == "execute" and _is_composed(sql))):
            unsafe.append(f"{path}:{node.lineno} {name}() with SQL that is not a fixed string")
    assert not unsafe, "Build queries with the ORM or pass values as parameters:\n" + "\n".join(unsafe)


def test_the_scan_finds_the_known_constant_query():
    found = [(str(path), name) for path, _node, name in _calls()]
    assert ("apps/core/views.py", "execute") in found


def test_composition_is_only_accepted_with_quoted_names_and_values():
    def verdict(source):
        return _is_composed(ast.parse(source, mode="eval").body)

    assert verdict('sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(a), sql.Identifier(b))')
    assert verdict('sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(a), sql.Literal(b))')
    assert not verdict('sql.SQL("ALTER ROLE {}").format(name)')  # a bare value
    assert not verdict('sql.SQL("ALTER ROLE " + name).format()')  # text built from a value
    assert not verdict("sql.SQL(template).format(sql.Identifier(a))")
    assert not verdict('sql.SQL("ALTER ROLE {x}").format(x=sql.SQL(name))')
    assert not verdict('"ALTER ROLE {}".format(name)')


def test_the_scan_sees_the_database_role_setup():
    found = {str(path) for path, _node, name in _calls() if name == "execute"}
    assert "apps/core/dbroles.py" in found
