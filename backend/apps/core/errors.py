"""Answers for requests Django refuses before any view runs (config/urls.py handler400).

Django's own page is HTML; the app expects JSON. A body over DATA_UPLOAD_MAX_MEMORY_SIZE, or one with too
many fields or files, is a 413 (Content Too Large) and a security event: nginx refuses such bodies first, so
one reaching Django means someone went around it or is probing.
"""

import logging

from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent
from django.http import JsonResponse
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
