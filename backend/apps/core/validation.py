"""Checks for single values a view reads from the query string or the request body.

Bodies with several fields go through a serializer; these helpers cover the odd id in a query
string (?classroom=12) or a single code in a body. A malformed value is a 400 with a clear message,
never a crash (500) or a database error, and an id is always a positive whole number.
"""

from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

# The largest id a PostgreSQL bigint can hold: anything larger can't name a row.
MAX_ID = 2**63 - 1


def parse_id(raw, name):
    """A positive whole number, or a 400 naming the field."""
    if isinstance(raw, bool) or raw is None:
        raise ValidationError({name: _("Enter a valid id.")})
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        raise ValidationError({name: _("Enter a valid id.")})
    if not 1 <= value <= MAX_ID:
        raise ValidationError({name: _("Enter a valid id.")})
    return value


def id_param(request, name):
    """?name=<id> as an int, or None when it isn't given."""
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    return parse_id(raw, name)


def int_param(request, name, minimum, maximum):
    """?name=<whole number between minimum and maximum>, or None when it isn't given."""
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        value = int(raw.strip())
    except ValueError:
        raise ValidationError({name: _("Enter a whole number.")})
    if not minimum <= value <= maximum:
        raise ValidationError({name: _("Enter a whole number.")})
    return value


def text_field(data, name, max_length, required=True):
    """A text value from a request body: must be a string (not a number or a list), at most max_length long."""
    raw = data.get(name, "")
    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        raise ValidationError({name: _("Enter text.")})
    value = raw.strip()
    if required and not value:
        raise ValidationError({name: _("This field is required.")})
    if len(value) > max_length:
        raise ValidationError({name: _("Use at most %(n)s characters.") % {"n": max_length}})
    return value
