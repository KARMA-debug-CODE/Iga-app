"""Requests refused before they reach a view."""

from django.http import JsonResponse

from .validation import NUL, contains_nul, nul_message


class RejectNulMiddleware:
    """A NUL character is never part of a valid Iga URL or query string, and PostgreSQL text can't hold one:
    refuse it with a 400 before a view passes it to the database, which would answer with an error (a 500).
    Request bodies get the same check in apps/core/parsers.py."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if NUL in request.path_info or contains_nul(request.GET):
            return JsonResponse({"detail": nul_message()}, status=400)
        return self.get_response(request)
