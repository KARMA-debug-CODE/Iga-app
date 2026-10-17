from rest_framework import serializers

from apps.core.text import CleanCharField
from apps.core.utils import serializer_language

from .models import LessonBookmark, LessonNote

NOTE_MAX_CHARS = 5000


def lesson_brief(lesson, lang):
    title = lesson.title
    if lang != "en":
        translation = next((t for t in lesson.translations.all() if t.language == lang), None)
        if translation:
            title = translation.title
    return {
        "slug": lesson.slug,
        "title": title,
        "subject": lesson.unit.subject.localized_name(lang),
        "icon": lesson.unit.subject.icon,
        "grade": lesson.unit.grade,
    }


class BookmarkSerializer(serializers.ModelSerializer):
    lesson = serializers.SerializerMethodField()

    class Meta:
        model = LessonBookmark
        fields = ["id", "lesson", "created_at"]

    def get_lesson(self, obj):
        return lesson_brief(obj.lesson, serializer_language(self))


class NoteSerializer(serializers.ModelSerializer):
    lesson = serializers.SerializerMethodField()

    class Meta:
        model = LessonNote
        fields = ["id", "lesson", "body", "updated_at", "created_at"]
        read_only_fields = ["id", "lesson", "updated_at", "created_at"]

    def get_lesson(self, obj):
        return lesson_brief(obj.lesson, serializer_language(self))


class NoteWriteSerializer(serializers.Serializer):
    """Create or update a note by lesson slug; an empty body deletes the note."""

    lesson = serializers.SlugField(max_length=120)
    body = CleanCharField(multiline=True, required=False, allow_blank=True, default="", max_length=NOTE_MAX_CHARS)


class BookmarkWriteSerializer(serializers.Serializer):
    lesson = serializers.SlugField(max_length=120)
