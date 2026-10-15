"""URL converters."""


class IdConverter:
    """<id:pk>: a database id. Like <int:...>, but at most 18 digits, so an absurdly long number in a
    URL is a 404 instead of a database overflow error (500). PostgreSQL bigints stop at 19 digits."""

    regex = "[0-9]{1,18}"

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return str(value)
