import logging

import anthropic
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.schools import access

from . import services

log = logging.getLogger(__name__)


class AskSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=services.MAX_MESSAGE_CHARS, trim_whitespace=True)
    history = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    lesson = serializers.SlugField(required=False, allow_blank=True)
    attempt = serializers.IntegerField(required=False, allow_null=True)
    question = serializers.IntegerField(required=False, allow_null=True)


class TutorStatusView(APIView):
    def get(self, request):
        premium = access.has_premium(request.user)
        return Response(
            {
                "enabled": services.tutor_enabled() and premium,
                # Set when the tutor exists but this account's school hasn't subscribed.
                "reason": "" if premium or not services.tutor_enabled() else "subscription_required",
            }
        )


class TutorAskView(APIView):
    throttle_scope = "tutor"

    def post(self, request):
        if not services.tutor_enabled():
            return Response(
                {"detail": "The AI tutor is not switched on for this school yet."}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        access.require(request.user)  # the tutor is part of the school subscription
        data = AskSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        try:
            reply = services.ask(
                request.user,
                v["message"],
                history=v.get("history"),
                lesson_slug=v.get("lesson") or None,
                attempt_id=v.get("attempt"),
                question_id=v.get("question"),
            )
        except anthropic.RateLimitError:
            return Response(
                {"detail": "The tutor is very busy right now. Try again in a minute."}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
            log.exception("Tutor credentials rejected by the Claude API")
            return Response(
                {"detail": "The AI tutor is not set up correctly. Please tell an administrator."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except anthropic.APIConnectionError:
            return Response(
                {"detail": "Couldn't reach the tutor. Check your connection and try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except anthropic.APIStatusError as exc:
            log.warning("Tutor request failed: %s (request id %s)", exc.status_code, getattr(exc, "request_id", None))
            return Response(
                {"detail": "The tutor couldn't answer just now. Please try again."}, status=status.HTTP_502_BAD_GATEWAY
            )
        return Response({"reply": reply})
