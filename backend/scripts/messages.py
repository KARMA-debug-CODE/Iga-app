"""Keep the French catalogue of the backend's own messages, without GNU gettext.

Django's makemessages/compilemessages need the xgettext and msgfmt programs, which many machines
and slim containers don't have. This script does the same for Iga:

    python scripts/messages.py extract   # add new _("...") messages to locale/fr/LC_MESSAGES/django.po
    python scripts/messages.py compile   # write django.mo from the .po (commit both files)

Messages are marked in the code with gettext / gettext_lazy imported as `_` (or `gettext_lazy`).
tests/test_translations.py fails when a marked message has no French translation, or when the
.mo is out of date.
"""

import ast
import struct
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
SOURCES = BACKEND / "apps"
CATALOGUE = BACKEND / "locale" / "fr" / "LC_MESSAGES" / "django.po"
MARKERS = {"_", "gettext", "gettext_lazy"}
HEADER = (
    'msgid ""\n'
    'msgstr ""\n'
    '"Content-Type: text/plain; charset=UTF-8\\n"\n'
    '"Language: fr\\n"\n'
    '"Plural-Forms: nplurals=2; plural=(n > 1);\\n"\n'
)


def extract():
    """{msgid: [file:line, ...]} for every marked message in the apps, in source order."""
    found = {}
    for path in sorted(SOURCES.rglob("*.py")):
        if "migrations" in path.parts or "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and node.args):
                continue
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
            first = node.args[0]
            if name in MARKERS and isinstance(first, ast.Constant) and isinstance(first.value, str) and first.value:
                found.setdefault(first.value, []).append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    return found


def _unquote(text):
    return ast.literal_eval(text)


def parse(path):
    """{msgid: msgstr} from a .po file (the header entry is skipped)."""
    messages = {}
    if not path.exists():
        return messages
    entry, key = {}, None

    def flush():
        if entry.get("msgid"):
            messages[entry["msgid"]] = entry.get("msgstr", "")
        entry.clear()

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            if not line:
                flush()
                key = None
            continue
        if line.startswith('"'):
            entry[key] += _unquote(line)
            continue
        word, _, rest = line.partition(" ")
        if word == "msgid" and "msgstr" in entry:
            flush()
        key = word
        entry[key] = _unquote(rest)
    flush()
    return messages


def _quote(text):
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
    return f'"{escaped}"'


def write_po(found, translations, path):
    parts = [HEADER]
    for msgid, places in found.items():
        refs = "\n".join(f"#: {place}" for place in places)
        parts.append(f"{refs}\nmsgid {_quote(msgid)}\nmsgstr {_quote(translations.get(msgid, ''))}\n")
    path.write_text("\n".join(parts), encoding="utf-8")


def mo_bytes(messages):
    """A GNU .mo file for {msgid: msgstr} (empty translations left out), header included."""
    messages = {k: v for k, v in messages.items() if v}
    messages[""] = "Content-Type: text/plain; charset=UTF-8\nLanguage: fr\nPlural-Forms: nplurals=2; plural=(n > 1);\n"
    keys = sorted(messages)
    ids = strs = b""
    offsets = []
    for k in keys:
        kid, kstr = k.encode("utf-8"), messages[k].encode("utf-8")
        offsets.append((len(ids), len(kid), len(strs), len(kstr)))
        ids += kid + b"\x00"
        strs += kstr + b"\x00"
    n = len(keys)
    key_start = 7 * 4 + 16 * n
    value_start = key_start + len(ids)
    key_table, value_table = [], []
    for id_off, id_len, str_off, str_len in offsets:
        key_table += [id_len, key_start + id_off]
        value_table += [str_len, value_start + str_off]
    header = struct.pack("Iiiiiii", 0x950412DE, 0, n, 7 * 4, 7 * 4 + 8 * n, 0, 0)
    return header + struct.pack(f"{2 * n}i", *key_table) + struct.pack(f"{2 * n}i", *value_table) + ids + strs


def main(command):
    if command == "extract":
        found = extract()
        existing = parse(CATALOGUE)
        write_po(found, existing, CATALOGUE)
        missing = [m for m in found if not existing.get(m)]
        dropped = [m for m in existing if m not in found]
        print(f"{len(found)} messages, {len(missing)} without a translation, {len(dropped)} no longer used (removed).")
        return 0
    if command == "compile":
        CATALOGUE.with_suffix(".mo").write_bytes(mo_bytes(parse(CATALOGUE)))
        print(f"Wrote {CATALOGUE.with_suffix('.mo').relative_to(BACKEND)}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
