from rest_framework import mixins, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.utils import request_language
from apps.curriculum.views import visible_lessons

from .models import LessonBookmark, LessonNote
from .serializers import (
    BookmarkSerializer,
    BookmarkWriteSerializer,
    NoteSerializer,
    NoteWriteSerializer,
    lesson_brief,
)

LESSON_SELECT = ("lesson", "lesson__unit", "lesson__unit__subject")


def resolve_lesson(user, slug):
    """A lesson the user may see (so a bookmark or note can't point at a hidden lesson)."""
    return get_object_or_404(
        visible_lessons(user).select_related("unit", "unit__subject").prefetch_related("translations"), slug=slug
    )


class BookmarkViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """A student's bookmarked lessons. Every query is scoped to the signed-in user."""

    serializer_class = BookmarkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            LessonBookmark.objects.filter(user=self.request.user)
            .select_related(*LESSON_SELECT)
            .prefetch_related("lesson__translations")
        )

    def create(self, request):
        data = BookmarkWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        lesson = resolve_lesson(request.user, data.validated_data["lesson"])
        bookmark, _created = LessonBookmark.objects.get_or_create(user=request.user, lesson=lesson)
        return Response(BookmarkSerializer(bookmark, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)


class NoteViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """A student's private per-lesson notes. Author-only: every query is scoped to the signed-in user."""

    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = (
            LessonNote.objects.filter(user=self.request.user)
            .select_related(*LESSON_SELECT)
            .prefetch_related("lesson__translations")
        )
        term = (self.request.query_params.get("q") or "").strip()
        if term:
            qs = qs.filter(body__icontains=term) | qs.filter(lesson__title__icontains=term)
        return qs.distinct()

    def create(self, request):
        """Upsert the note for a lesson. An empty body removes the note."""
        data = NoteWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        lesson = resolve_lesson(request.user, data.validated_data["lesson"])
        body = data.validated_data["body"].strip()
        if not body:
            LessonNote.objects.filter(user=request.user, lesson=lesson).delete()
            return Response({"deleted": True}, status=status.HTTP_200_OK)
        note, _created = LessonNote.objects.update_or_create(user=request.user, lesson=lesson, defaults={"body": body})
        note = self.get_queryset().get(pk=note.pk)
        return Response(NoteSerializer(note, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)


class LessonNotesStateView(APIView):
    """The signed-in student's bookmark and note for one lesson, for the lesson page."""

    permission_classes = [IsAuthenticated]

    def get(self, request, slug=None):
        lesson = resolve_lesson(request.user, slug)
        bookmark = LessonBookmark.objects.filter(user=request.user, lesson=lesson).first()
        note = LessonNote.objects.filter(user=request.user, lesson=lesson).first()
        lang = request_language(request)
        return Response(
            {
                "lesson": lesson_brief(lesson, lang),
                "bookmarked": bookmark is not None,
                "bookmark_id": bookmark.id if bookmark else None,
                "note": {"id": note.id, "body": note.body, "updated_at": note.updated_at} if note else None,
            }
        )
