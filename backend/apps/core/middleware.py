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


class SecurityHeadersMiddleware:
    """Security headers Django's SecurityMiddleware doesn't send, on every answer from Django (nginx sends its own
    on the app's pages, frontend/nginx/headers-app.conf). A view may set its own; these are only defaults.

    - Content-Security-Policy: API answers are JSON or files, which need nothing at all (and may not be framed);
      the Django admin's pages use only its own scripts, plus inline styles.
    - Permissions-Policy: no camera, microphone, location, payment or device APIs.
    - Cross-Origin-Resource-Policy: other sites can't embed Iga's answers.
    (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Cross-Origin-Opener-Policy and HSTS come from
    Django's own middleware, see the SECURE_* settings.)
    """

    API_POLICY = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ADMIN_POLICY = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    PERMISSIONS_POLICY = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), hid=(), bluetooth=(), midi=(), "
        "display-capture=(), browsing-topics=()"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        admin = request.path.startswith(("/django-admin/", "/static/"))
        response.headers.setdefault("Content-Security-Policy", self.ADMIN_POLICY if admin else self.API_POLICY)
        response.headers.setdefault("Permissions-Policy", self.PERMISSIONS_POLICY)
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return response
