"""Small helpers for the apps' userdata.export_for(): plain JSON values (no datetimes or Decimals)."""


def iso(value):
    """A date or datetime as ISO 8601 text, or None."""
    return value.isoformat() if value is not None else None


def number(value):
    """A Decimal (a score, an amount) as text that keeps every digit, or None."""
    return str(value) if value is not None else None
