import json
import logging

from django.http import StreamingHttpResponse
from django.utils.translation import gettext as _
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import security_log
from apps.core.text import CleanCharField
from apps.schools import access

from . import services

# The most earlier messages a request may carry (the server reads only the last MAX_HISTORY_MESSAGES).
MAX_HISTORY_ITEMS = 50
# Santa's longest answers (a full answer plus notes, or lesson passages) are far shorter than this.
MAX_HISTORY_CONTENT = 20_000


class AskSerializer(serializers.Serializer):
    message = CleanCharField(multiline=True, max_length=services.MAX_MESSAGE_CHARS, trim_whitespace=True)
    history = serializers.ListField(child=serializers.DictField(), required=False, default=list, max_length=MAX_HISTORY_ITEMS)
    lesson = serializers.SlugField(required=False, allow_blank=True)
    attempt = serializers.IntegerField(required=False, allow_null=True)
    question = serializers.IntegerField(required=False, allow_null=True)
    lang = serializers.ChoiceField(choices=list(services.LANGUAGE_NAMES), required=False)
    subject = serializers.SlugField(required=False, allow_blank=True)

    def validate_history(self, value):
        for item in value:
            content = item.get("content")
            if isinstance(content, str) and len(content) > MAX_HISTORY_CONTENT:
                raise serializers.ValidationError(_("A message in the history is too long."))
        return value


def _prepare(request):
    """Check access and the question (403, 400 or 404 answers come from here, before any answering)."""
    access.require(request.user)  # Santa is part of the school subscription
    data = AskSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    v = data.validated_data
    prepared = services.prepare(
        request.user,
        v["message"],
        history=v.get("history"),
        lesson_slug=v.get("lesson") or None,
        attempt_id=v.get("attempt"),
        question_id=v.get("question"),
        lang=v.get("lang"),
        subject_code=v.get("subject") or None,
    )
    # Attempts to steer Santa are security events (at most one audit entry per student and kind in 10 minutes;
    # every question is in Santa's exchange log, flagged, for safeguarding review).
    if prepared.suspicious:
        security_log.event(request, "santa_injection", request.user, level=logging.WARNING, audit_every=600)
    if prepared.forged:
        security_log.event(
            request, "santa_forged_history", request.user, level=logging.WARNING, audit_every=600, dropped=prepared.forged
        )
    return prepared


class TutorStatusView(APIView):
    def get(self, request):
        return Response(services.status(request.user))


class TutorAskView(APIView):
    """Santa's whole answer as JSON: {reply, sources, fallback, tools, allowance}."""

    throttle_scope = "tutor"

    def post(self, request):
        prepared = _prepare(request)
        events = services.answer(prepared, stream=False)
        try:
            for event in events:
                if event["type"] == "error":
                    return Response({"detail": event["detail"], "code": event["code"]}, status=status.HTTP_429_TOO_MANY_REQUESTS)
                if event["type"] == "done":
                    return Response({key: event[key] for key in ("reply", "sources", "fallback", "tools", "allowance")})
        finally:
            events.close()  # frees this student's turn and the model slot now
        return Response(status=status.HTTP_502_BAD_GATEWAY)


class _EventStream:
    """Server-Sent Events from Santa's answer events. Closing it (the student pressed Stop, or the response
    ended) closes the answer, which logs it and closes the connection to the model server."""

    def __init__(self, events):
        self.events = events

    def __iter__(self):
        for event in self.events:
            if event["type"] == "ping":
                yield ": ping\n\n"
            else:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    def close(self):
        self.events.close()


class TutorStreamView(APIView):
    """Santa's answer as it is written, as Server-Sent Events (text/event-stream) over this POST:
    `data: {"type": "start" | "delta" | "tool" | "done" | "error", ...}` lines, and ": ping" comments."""

    throttle_scope = "tutor"

    def perform_content_negotiation(self, request, force=False):
        # Browsers ask for text/event-stream; errors before the stream starts are still sent as JSON.
        return super().perform_content_negotiation(request, force=True)

    def post(self, request):
        prepared = _prepare(request)
        response = StreamingHttpResponse(
            _EventStream(services.answer(prepared, stream=True)), content_type="text/event-stream; charset=utf-8"
        )
        response["Cache-Control"] = "no-cache, no-store"
        # nginx: pass each piece on at once instead of buffering the answer.
        response["X-Accel-Buffering"] = "no"
        return response
