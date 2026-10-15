"""Every URL the API serves, listed from Django's URL resolver (so a new route is never missed)."""

import re

from django.urls import get_resolver
from django.urls.resolvers import URLResolver

# Path parameters as the router writes them: (?P<pk>[^/.]+) or <int:pk> / <str:token>.
_REGEX_PARAM = re.compile(r"\(\?P<(\w+)>[^)]*\)")
_PATH_PARAM = re.compile(r"<(?:(\w+):)?(\w+)>")


def _walk(patterns, prefix=""):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _walk(pattern.url_patterns, prefix + str(pattern.pattern))
        else:
            yield prefix + str(pattern.pattern), pattern.callback


def _normalise(raw):
    """'api/^classes/(?P<pk>[^/.]+)/report/$' -> 'api/classes/{pk}/report/'."""
    text = raw.replace("^", "").replace("$", "")
    text = _REGEX_PARAM.sub(lambda m: "{" + m.group(1) + "}", text)
    text = _PATH_PARAM.sub(lambda m: "{" + m.group(2) + "}", text)
    return text


def api_routes():
    """[(route, view callback)] for every /api/ route, without DRF's ".json" format-suffix copies."""
    routes = {}
    for raw, callback in _walk(get_resolver().url_patterns):
        if "format" in raw:
            continue
        route = _normalise(raw)
        if route.startswith("api/"):
            routes.setdefault(route, callback)
    return sorted(routes.items())


def view_methods(callback):
    """The HTTP methods a route answers (DRF viewsets map them in .actions; APIViews define handlers)."""
    actions = getattr(callback, "actions", None)
    if actions:
        return sorted(m.upper() for m in actions)
    cls = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
    if cls is None:
        return ["GET"]
    return sorted(m.upper() for m in ("get", "post", "put", "patch", "delete") if hasattr(cls, m))


def view_class(callback):
    return getattr(callback, "cls", None) or getattr(callback, "view_class", None)


def fill(route, **values):
    """'api/classes/{pk}/report/' with pk=3 -> '/api/classes/3/report/'."""
    return "/" + re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), values.get("default", "1"))), route)
