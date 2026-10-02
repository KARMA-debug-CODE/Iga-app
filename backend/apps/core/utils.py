from apps.core.constants import GRADE_CODES, LANGUAGE_CODES


def request_language(request):
    """?lang= wins, then the user's saved preference, then English."""
    lang = request.query_params.get("lang") if hasattr(request, "query_params") else None
    if lang in LANGUAGE_CODES:
        return lang
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.preferred_language in LANGUAGE_CODES:
        return user.preferred_language
    return "en"


def request_grade(request, default_to_user=True):
    grade = request.query_params.get("grade")
    if grade in GRADE_CODES:
        return grade
    if default_to_user and request.user.is_authenticated and request.user.grade:
        return request.user.grade
    return None
