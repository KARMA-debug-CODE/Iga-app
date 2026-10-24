import logging

from django.utils.translation import gettext as _
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import security_log
from apps.schools import access

from . import services

log = logging.getLogger(__name__)


class RunSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=list(services.LANGUAGES))
    code = serializers.CharField(max_length=services.MAX_CODE_CHARS, trim_whitespace=False)


class InputSerializer(serializers.Serializer):
    session = serializers.CharField(max_length=64)
    text = serializers.CharField(max_length=services.MAX_INPUT_CHARS, allow_blank=True, trim_whitespace=False)


class StopSerializer(serializers.Serializer):
    session = serializers.CharField(max_length=64)


def _off():
    return Response(
        {"detail": _("C++ and Java are not switched on for this server yet."), "code": "not_configured"},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _check(request, starting, session=None):
    """403 when this user may not use the runner; 429 when a daily limit is used up (the program waiting for
    an answer is ended then). None when the request may go on."""
    user = request.user
    if not services.may_use(user):
        raise access.SubscriptionRequired()
    if not services.limit_reached(user.pk, starting):
        return None
    services.record(user.pk, limited=True)
    if session:
        services.stop(user.pk, session)
    security_log.event(request, "code_run_limit", user, level=logging.WARNING, audit_every=6 * 3600)
    detail = _(
        "You have used today's time on the code runner. C++ and Java can run again tomorrow; "
        "Python, SQL and web pages still run in your browser."
    )
    return Response({"detail": detail, "code": "daily_limit"}, status=status.HTTP_429_TOO_MANY_REQUESTS)


def _call(request, action):
    """Run one step on the code runner and turn its problems into clear answers."""
    try:
        with services.one_request_at_a_time(request.user.pk):
            result = action()
    except services.AlreadyRunning:
        return Response(
            {"detail": _("Your last program is still running. Wait for it to finish."), "code": "already_running"},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except services.RunnerUnavailable as exc:
        log.warning("Code runner unavailable: %s", exc)
        return Response(
            {"detail": _("The code runner is not answering. Try again in a minute."), "code": "unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except services.RunnerError as exc:
        log.error("Code runner error: %s", exc)
        return Response(
            {"detail": _("The code runner could not run this program. Please tell an administrator."), "code": "error"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    if result is None:
        return Response(
            {"detail": _("This program has already finished. Press Run to start it again."), "code": "gone"},
            status=status.HTTP_410_GONE,
        )
    if result.get("verdict") == "busy":
        return Response(
            {"detail": _("Many students are running programs right now. Try again in a few seconds."), "code": "busy"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({key: result.get(key) for key in ("session", "state", "output", "verdict", "exit_code", "signal")})


class CodeStatusView(APIView):
    def get(self, request):
        allowed = services.may_use(request.user)
        return Response(
            {
                "enabled": services.enabled(),
                "languages": list(services.LANGUAGES),
                "allowed": allowed,
                "allowance": services.allowance(request.user.pk) if allowed else None,
            }
        )


class CodeRunView(APIView):
    """Start a C++ or Java program (Python and SQL run in the browser)."""

    throttle_scope = "code_run"

    def post(self, request):
        if not services.enabled():
            return _off()
        data = RunSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        refused = _check(request, starting=True)
        if refused is not None:
            return refused
        return _call(request, lambda: services.run(request.user.pk, v["language"], v["code"]))


class CodeInputView(APIView):
    """Send the student's answer to a program that is waiting for keyboard input."""

    throttle_scope = "code_input"

    def post(self, request):
        if not services.enabled():
            return _off()
        data = InputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        if not services.owns(request.user.pk, v["session"]):
            return Response(
                {"detail": _("This program has already finished. Press Run to start it again."), "code": "gone"},
                status=status.HTTP_410_GONE,
            )
        refused = _check(request, starting=False, session=v["session"])
        if refused is not None:
            return refused
        return _call(request, lambda: services.send_input(request.user.pk, v["session"], v["text"]))


class CodeStopView(APIView):
    def post(self, request):
        data = StopSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.stop(request.user.pk, data.validated_data["session"])
        return Response({"stopped": True})
