"""Checks for single values a view reads from the query string or the request body.

Bodies with several fields go through a serializer; these helpers cover the odd id in a query
string (?classroom=12) or a single code in a body. A malformed value is a 400 with a clear message,
never a crash (500) or a database error, and an id is always a positive whole number.
"""

from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

# The largest id a PostgreSQL bigint can hold: anything larger can't name a row.
MAX_ID = 2**63 - 1
# PostgreSQL text can't hold the NUL character, and no Iga field ever needs it.
NUL = "\x00"


def nul_message():
    return _("The request contains a character that is not allowed.")


def contains_nul(value):
    """True if a parsed request value (text, lists and dicts of it, keys included, or a QueryDict) holds a NUL
    character. Walks without recursion, so deeply nested JSON can't overflow the stack."""
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            if NUL in item:
                return True
        elif hasattr(item, "lists"):  # QueryDict / MultiValueDict: every value, not only the last
            for key, values in item.lists():
                stack.append(key)
                stack.extend(values)
        elif isinstance(item, dict):
            for key, child in item.items():
                stack.append(key)
                stack.append(child)
        elif isinstance(item, (list, tuple)):
            stack.extend(item)
    return False


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
    if NUL in raw:
        raise ValidationError({name: nul_message()})
    value = raw.strip()
    if required and not value:
        raise ValidationError({name: _("This field is required.")})
    if len(value) > max_length:
        raise ValidationError({name: _("Use at most %(n)s characters.") % {"n": max_length}})
    return value
