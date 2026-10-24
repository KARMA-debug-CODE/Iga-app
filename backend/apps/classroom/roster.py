"""Create student accounts for a class from a CSV list (many students have no email).

Every account starts with a temporary password the teacher hands out; the student must
choose their own at first login. The temporary passwords are only returned once.
"""

import csv
import io
import re
import secrets
import unicodedata
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.accounts.security import revoke_all_sessions
from apps.core.text import clean_text

from .models import Enrollment

MAX_ROWS = 200
COLUMNS = {
    "first_name": {"first_name", "firstname", "first", "given_name", "izina", "jina"},
    "last_name": {"last_name", "lastname", "surname", "family_name", "irindi_zina", "jina_la_ukoo"},
    "name": {"name", "full_name", "student", "student_name", "amazina"},
    "username": {"username", "user", "login"},
    "email": {"email", "e-mail", "email_address"},
}
# Easy to read aloud and type on a phone: two short words and four digits.
WORDS = [
    "amazi", "icyayi", "ikawa", "igiti", "inka", "inyoni", "inzovu", "izuba", "ubuki", "umusozi",
    "jua", "maji", "mlima", "ndege", "nyota", "tembo", "simba", "kivu", "moto", "zebra",
]  # fmt: skip


class RosterError(Exception):
    pass


def temporary_password_expiry():
    """When a temporary password handed out now stops working (TEMPORARY_PASSWORD_DAYS)."""
    return timezone.now() + timedelta(days=settings.TEMPORARY_PASSWORD_DAYS)


def temporary_password(user=None):
    while True:
        password = f"{secrets.choice(WORDS)}-{secrets.choice(WORDS)}-{secrets.randbelow(10000):04d}"
        try:
            password_validation.validate_password(password, user)
            return password
        except ValidationError:
            continue


def _ascii(value):
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()


def _base_username(first, last):
    parts = [re.sub(r"[^a-z0-9]", "", _ascii(p)) for p in (first, last)]
    return ".".join(p for p in parts if p)[:30] or "student"


def _canonical(header):
    key = (header or "").strip().lower().replace(" ", "_")
    for name, aliases in COLUMNS.items():
        if key in aliases:
            return name
    return None


def parse(text):
    """Rows as dicts with first_name, last_name, username, email (and the CSV line number)."""
    text = (text or "").lstrip("\ufeff").strip()
    if not text:
        raise RosterError(_("The list is empty."))
    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    header = [_canonical(h) for h in next(reader)]
    if "first_name" not in header and "name" not in header:
        raise RosterError(_("The first row must name the columns, e.g. first_name,last_name (username and email are optional)."))
    rows = []
    for line, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue
        row = {"line": line, "first_name": "", "last_name": "", "username": "", "email": ""}
        for column, value in zip(header, values, strict=False):
            if column:
                # One line each, without invisible or control characters (apps/core/text.py).
                row[column] = clean_text(value).strip()
        full_name = row.pop("name", "")
        if full_name and not row["first_name"]:
            first, _space, last = full_name.partition(" ")
            row["first_name"], row["last_name"] = first, row["last_name"] or last.strip()
        rows.append(row)
    if len(rows) > MAX_ROWS:
        raise RosterError(_("Import at most %(n)s students at a time.") % {"n": MAX_ROWS})
    if not rows:
        raise RosterError(_("No students found under the header row."))
    return rows


def check(rows):
    """Fill in usernames and attach a list of problems to each row. Returns True if all rows are fine."""
    validator = UnicodeUsernameValidator()
    chosen = set()
    ok = True
    for row in rows:
        errors = []
        if not row["first_name"]:
            errors.append(_("First name is missing."))
        if len(row["first_name"]) > 150 or len(row["last_name"]) > 150:
            errors.append(_("Name is too long."))
        if row["username"]:
            try:
                validator(row["username"])
            except ValidationError:
                errors.append(_("Usernames may use letters, numbers and . _ - only."))
            if "@" in row["username"]:
                errors.append(_("Usernames can't contain @."))
            if User.objects.filter(username__iexact=row["username"]).exists():
                errors.append(_("That username is already taken."))
            if row["username"].lower() in chosen:
                errors.append(_("That username appears twice in the list."))
        elif row["first_name"]:
            base, n = _base_username(row["first_name"], row["last_name"]), 1
            candidate = base
            while candidate in chosen or User.objects.filter(username__iexact=candidate).exists():
                n += 1
                candidate = f"{base}{n}"
            row["username"] = candidate
        if row["email"]:
            try:
                validate_email(row["email"])
                if User.objects.filter(email__iexact=row["email"]).exists():
                    errors.append(_("That email is already used by another account."))
            except ValidationError:
                errors.append(_("That email address isn't valid."))
        chosen.add(row["username"].lower())
        row["errors"] = errors
        ok = ok and not errors
    return ok


@transaction.atomic
def create_accounts(rows, classroom, teacher):
    created = []
    for row in rows:
        user = User(
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            email=row["email"].lower() or None,
            role=User.Role.STUDENT,
            grade=classroom.grade,
            must_change_password=True,
            temporary_password_expires_at=temporary_password_expiry(),
        )
        # They join the teacher's school straight away: the teacher vouches for their own class.
        school = teacher.school_member
        if school is not None:
            user.school = school
            user.school_status = User.SchoolStatus.APPROVED
            user.school_approved_at = timezone.now()
            user.school_approved_by = teacher
        password = temporary_password(user)
        user.set_password(password)
        user.save()
        Enrollment.objects.create(classroom=classroom, student=user)
        created.append({**{k: row[k] for k in ("line", "first_name", "last_name", "username")}, "temporary_password": password})
    return created


def reset_password(student):
    password = temporary_password(student)
    student.set_password(password)
    student.must_change_password = True
    student.temporary_password_expires_at = temporary_password_expiry()
    student.save(update_fields=["password", "must_change_password", "temporary_password_expires_at"])
    revoke_all_sessions(student)
    return password
