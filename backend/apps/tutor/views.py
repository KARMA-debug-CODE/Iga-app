import json

from django.http import StreamingHttpResponse
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.schools import access

from . import services


class AskSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=services.MAX_MESSAGE_CHARS, trim_whitespace=True)
    history = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    lesson = serializers.SlugField(required=False, allow_blank=True)
    attempt = serializers.IntegerField(required=False, allow_null=True)
    question = serializers.IntegerField(required=False, allow_null=True)
    lang = serializers.ChoiceField(choices=list(services.LANGUAGE_NAMES), required=False)
    subject = serializers.SlugField(required=False, allow_blank=True)


def _prepare(request):
    """Check access and the question (403, 400 or 404 answers come from here, before any answering)."""
    access.require(request.user)  # Santa is part of the school subscription
    data = AskSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    v = data.validated_data
    return services.prepare(
        request.user,
        v["message"],
        history=v.get("history"),
        lesson_slug=v.get("lesson") or None,
        attempt_id=v.get("attempt"),
        question_id=v.get("question"),
        lang=v.get("lang"),
        subject_code=v.get("subject") or None,
    )


class TutorStatusView(APIView):
    def get(self, request):
        return Response(services.status(request.user))


class TutorAskView(APIView):
    """Santa's whole answer as JSON: {reply, sources, fallback, tools}."""

    throttle_scope = "tutor"

    def post(self, request):
        prepared = _prepare(request)
        events = services.answer(prepared, stream=False)
        try:
            for event in events:
                if event["type"] == "error":
                    return Response({"detail": event["detail"], "code": event["code"]}, status=status.HTTP_429_TOO_MANY_REQUESTS)
                if event["type"] == "done":
                    return Response({key: event[key] for key in ("reply", "sources", "fallback", "tools")})
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
