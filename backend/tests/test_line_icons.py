"""Subjects and badges store the names of line icons drawn by the frontend (no emojis)."""

import json
import re

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.core.content_loader import DEFAULT_CONTENT_DIR
from apps.gamification.services import BADGES

ICON_FILE = DEFAULT_CONTENT_DIR.parent.parent / "frontend" / "src" / "components" / "Icon.jsx"


def frontend_icon_names():
    source = ICON_FILE.read_text(encoding="utf-8")
    block = source.split("const ICONS = {", 1)[1].split("};", 1)[0]
    return set(re.findall(r"^\s+(\w+): \w+,$", block, re.MULTILINE))


def test_subject_and_badge_icons_are_icons_the_app_draws():
    names = frontend_icon_names()
    assert {"book", "award", "sigma"} <= names
    subjects = json.loads((DEFAULT_CONTENT_DIR / "subjects.json").read_text(encoding="utf-8"))
    assert {s["code"]: s["icon"] for s in subjects if s["icon"] not in names} == {}
    assert {code: icon for code, (_, _, icon) in BADGES.items() if icon not in names} == {}


@pytest.mark.django_db(transaction=True)
def test_migrations_turn_old_emojis_into_icon_names():
    before = [("curriculum", "0006_resource_books"), ("gamification", "0001_initial")]
    after = [("curriculum", "0007_line_icons"), ("gamification", "0002_line_icons")]
    executor = MigrationExecutor(connection)
    executor.migrate(before)
    try:
        old = executor.loader.project_state(before).apps
        Subject, Badge = old.get_model("curriculum", "Subject"), old.get_model("gamification", "Badge")
        Subject.objects.create(code="physics", name="Physics", icon="\u26a1")
        Subject.objects.create(code="chemistry", name="Chemistry", icon="\u2697\ufe0f")
        Subject.objects.create(code="drama", name="Drama", icon="\U0001f3ad")
        Subject.objects.create(code="music", name="Music", icon="\U0001f3b5")
        Badge.objects.create(code="streak-7", name="Unstoppable", description="7 days", icon="\u26a1")
        Badge.objects.create(code="helper", name="Helper", description="Helped", icon="\U0001f3c5")

        executor = MigrationExecutor(connection)
        executor.migrate(after)
        new = executor.loader.project_state(after).apps
        icons = dict(new.get_model("curriculum", "Subject").objects.values_list("code", "icon"))
        assert icons == {"physics": "atom", "chemistry": "flask", "drama": "scroll", "music": "book"}
        badges = dict(new.get_model("gamification", "Badge").objects.values_list("code", "icon"))
        assert badges == {"streak-7": "zap", "helper": "award"}

        # And back: the old field only holds a few characters, so names turn into emojis again.
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        old = executor.loader.project_state(before).apps
        assert old.get_model("curriculum", "Subject").objects.get(code="physics").icon == "\u26a1"
        assert old.get_model("gamification", "Badge").objects.get(code="helper").icon == "\U0001f3c5"
    finally:
        MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
