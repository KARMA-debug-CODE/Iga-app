"""DRF's body parsers, refusing text that holds a NUL character (see apps/core/middleware.py).

Serializers' text fields already refuse it; these also cover values a view reads straight from
request.data, and dictionary keys, so no NUL ever reaches the database (a 400, not a 500)."""

from rest_framework import parsers
from rest_framework.exceptions import ParseError

from .validation import contains_nul, nul_message


class JSONParser(parsers.JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        data = super().parse(stream, media_type, parser_context)
        if contains_nul(data):
            raise ParseError(nul_message())
        return data


class FormParser(parsers.FormParser):
    def parse(self, stream, media_type=None, parser_context=None):
        data = super().parse(stream, media_type, parser_context)
        if contains_nul(data):
            raise ParseError(nul_message())
        return data


class MultiPartParser(parsers.MultiPartParser):
    def parse(self, stream, media_type=None, parser_context=None):
        result = super().parse(stream, media_type, parser_context)
        if contains_nul(result.data):  # the text fields; uploaded files are checked by apps/core/uploads.py
            raise ParseError(nul_message())
        return result
