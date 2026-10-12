"""Every database query is parameterised: no SQL is ever built from strings.

All data access goes through the Django ORM, which sends values as query parameters. This test reads
the source of every app and fails on any raw SQL whose text is not a fixed string literal, so a value
can never be pasted into a query (the only raw SQL today is the health check's constant "SELECT 1").
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


def test_raw_sql_is_only_ever_a_constant_with_parameters():
    unsafe = []
    for path, node, name in _calls():
        if name == "extra":
            unsafe.append(f"{path}:{node.lineno} .extra() (use the ORM)")
            continue
        sql = node.args[0] if node.args else None
        if not (isinstance(sql, ast.Constant) and isinstance(sql.value, str)):
            unsafe.append(f"{path}:{node.lineno} {name}() with SQL that is not a fixed string")
    assert not unsafe, "Build queries with the ORM or pass values as parameters:\n" + "\n".join(unsafe)


def test_the_scan_finds_the_known_constant_query():
    found = [(str(path), name) for path, _node, name in _calls()]
    assert ("apps/core/views.py", "execute") in found
