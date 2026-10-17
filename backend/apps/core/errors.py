"""Answers for requests Django refuses before any view runs (config/urls.py handler400), and for unexpected
errors (handler500).

Django's own page is HTML; the app expects JSON. A body over DATA_UPLOAD_MAX_MEMORY_SIZE, or one with too
many fields or files, is a 413 (Content Too Large) and a security event: nginx refuses such bodies first, so
one reaching Django means someone went around it or is probing.
"""

import logging

from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent
from django.http import HttpResponse, JsonResponse
from django.utils.html import escape
from django.utils.translation import gettext as _

from . import security_log


def bad_request(request, exception=None):
    if isinstance(exception, RequestDataTooBig):
        detail, status, reason = _("This request is too large."), 413, "body"
    elif isinstance(exception, (TooManyFieldsSent, TooManyFilesSent)):
        detail, status, reason = _("This request has too many fields or files."), 413, "fields"
    else:
        return JsonResponse({"detail": _("Bad request.")}, status=400)
    security_log.event(request, "request_too_large", None, level=logging.WARNING, audit_every=600, reason=reason)
    return JsonResponse({"detail": detail}, status=status)


def server_error(request):
    """An unexpected error (the details are in the server log, never in the answer). The app reads JSON; the
    Django admin and the other pages get a short page in the reader's language."""
    detail = _("Something went wrong on our side. Please try again in a few minutes.")
    if request.path.startswith("/api/"):
        return JsonResponse({"detail": detail, "code": "server_error"}, status=500)
    title = escape(_("Something went wrong"))
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        f"<title>{title}</title></head><body style='font-family:system-ui,sans-serif;max-width:32rem;margin:15vh auto;"
        f"padding:0 16px;line-height:1.5'><h1>{title}</h1><p>{escape(detail)}</p><p><a href='/'>Iga</a></p></body></html>"
    )
    return HttpResponse(page, status=500, content_type="text/html; charset=utf-8")
