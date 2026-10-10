import logging

from django.utils.translation import gettext as _
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

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
        return Response({"enabled": services.enabled(), "languages": list(services.LANGUAGES)})


class CodeRunView(APIView):
    """Start a C++ or Java program (Python and SQL run in the browser)."""

    throttle_scope = "code_run"

    def post(self, request):
        if not services.enabled():
            return _off()
        data = RunSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
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
        return _call(request, lambda: services.send_input(request.user.pk, v["session"], v["text"]))


class CodeStopView(APIView):
    def post(self, request):
        data = StopSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.stop(request.user.pk, data.validated_data["session"])
        return Response({"stopped": True})
