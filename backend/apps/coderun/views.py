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
    stdin = serializers.CharField(
        max_length=services.MAX_STDIN_CHARS, required=False, allow_blank=True, trim_whitespace=False, default=""
    )


class CodeStatusView(APIView):
    def get(self, request):
        return Response({"enabled": services.enabled(), "languages": list(services.LANGUAGES)})


class CodeRunView(APIView):
    """Run a C++ or Java program for the playground (Python and SQL run in the browser)."""

    throttle_scope = "code_run"

    def post(self, request):
        if not services.enabled():
            return Response(
                {"detail": _("C++ and Java are not switched on for this server yet."), "code": "not_configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        data = RunSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        try:
            result = services.run(v["language"], v["code"], v.get("stdin", ""))
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
        return Response(result)
