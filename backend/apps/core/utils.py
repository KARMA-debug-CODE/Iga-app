from django.utils import translation

from apps.core.constants import GRADE_CODES, LANGUAGE_CODES


def request_language(request):
    """?lang= wins, then the language the app is shown in (sent as Accept-Language and picked by
    LocaleMiddleware), then the user's saved preference, then English."""
    lang = request.query_params.get("lang") if hasattr(request, "query_params") else None
    if lang in LANGUAGE_CODES:
        return lang
    if request.META.get("HTTP_ACCEPT_LANGUAGE"):
        active = (translation.get_language() or "")[:2]
        if active in LANGUAGE_CODES:
            return active
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.preferred_language in LANGUAGE_CODES:
        return user.preferred_language
    return "en"


def serializer_language(serializer):
    """The reader's language for a serializer: its context's "lang", else the request's."""
    lang = serializer.context.get("lang")
    if lang in LANGUAGE_CODES:
        return lang
    request = serializer.context.get("request")
    return request_language(request) if request is not None else "en"


def request_grade(request, default_to_user=True):
    grade = request.query_params.get("grade")
    if grade in GRADE_CODES:
        return grade
    if default_to_user and request.user.is_authenticated and request.user.grade:
        return request.user.grade
    return None
