from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.core.constants import ContentStatus
from apps.core.utils import serializer_language
from apps.schools.access import content_access

from .models import Lesson, LessonTranslation, Resource, Subject, Unit


class SubjectSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    unit_count = serializers.IntegerField(read_only=True, required=False)
    lesson_count = serializers.IntegerField(read_only=True, required=False)
    completed_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Subject
        fields = [
            "id",
            "code",
            "name",
            "display_name",
            "description",
            "category",
            "icon",
            "color",
            "offered_o_level",
            "offered_a_level",
            "unit_count",
            "lesson_count",
            "completed_count",
        ]

    def get_display_name(self, subject):
        return subject.localized_name(self.context.get("lang", "en"))


def is_locked(serializer, item):
    """Free items are open to everyone; the rest need premium access (decided once per request)."""
    if item.is_free:
        return False
    request = serializer.context.get("request")
    return not content_access(request.user if request else None).premium


class LessonSummarySerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ["id", "slug", "order", "title", "summary", "estimated_minutes", "status", "completed", "is_free", "locked"]

    def get_title(self, lesson):
        translation = self.context.get("translations", {}).get(lesson.id)
        return translation.title if translation else lesson.title

    def get_summary(self, lesson):
        translation = self.context.get("translations", {}).get(lesson.id)
        return translation.summary if translation and translation.summary else lesson.summary

    def get_locked(self, lesson):
        return is_locked(self, lesson)

    def get_completed(self, lesson):
        return lesson.id in self.context.get("completed_ids", set())


class UnitSerializer(serializers.ModelSerializer):
    lessons = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    # Both titles, so the app can name the unit in the language of each textbook.
    title_en = serializers.CharField(source="title", read_only=True)

    class Meta:
        model = Unit
        fields = [
            "id",
            "grade",
            "number",
            "title",
            "title_en",
            "title_fr",
            "summary",
            "key_unit_competence",
            "syllabus_reference",
            "alignment_verified",
            "lessons",
        ]

    def get_title(self, unit):
        return unit.localized_title(self.context.get("lang", "en"))

    def get_lessons(self, unit):
        lessons = self.context["lessons_by_unit"].get(unit.id, [])
        return LessonSummarySerializer(lessons, many=True, context=self.context).data


class ResourceSerializer(serializers.ModelSerializer):
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = [
            "id",
            "subject",
            "subject_code",
            "grade",
            "unit",
            "kind",
            "title",
            "description",
            "description_fr",
            "url",
            "format",
            "file",
            "file_url",
            "language",
            "publisher",
            "licence",
            "is_official",
            "status",
            "created_at",
        ]
        read_only_fields = ["status", "created_at", "is_official"]
        extra_kwargs = {"file": {"write_only": True, "required": False}}

    def get_file_url(self, resource):
        if not resource.file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(resource.file.url) if request else resource.file.url

    def validate(self, attrs):
        if not attrs.get("url") and not attrs.get("file") and not (self.instance and (self.instance.url or self.instance.file)):
            raise serializers.ValidationError(_("Provide a link or upload a file."))
        return attrs


class LessonDetailSerializer(serializers.ModelSerializer):
    """Read view: applies the requested language when a translation exists."""

    title = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()
    author_name = serializers.CharField(source="author.display_name", read_only=True, default=None)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "slug",
            "order",
            "title",
            "summary",
            "is_free",
            "locked",
            "body",
            "language",
            "available_languages",
            "video_url",
            "estimated_minutes",
            "status",
            "unit",
            "subject",
            "completed",
            "author_name",
            "updated_at",
        ]

    def _translation(self, lesson):
        if not hasattr(lesson, "_translation_cache"):
            lang = self.context.get("lang", "en")
            lesson._translation_cache = lesson.translations.filter(language=lang).first() if lang != "en" else None
        return lesson._translation_cache

    def get_title(self, lesson):
        t = self._translation(lesson)
        return t.title if t else lesson.title

    def get_summary(self, lesson):
        t = self._translation(lesson)
        return t.summary if t else lesson.summary

    def get_locked(self, lesson):
        return is_locked(self, lesson)

    def get_body(self, lesson):
        if is_locked(self, lesson):
            return ""  # the full lesson needs a school subscription
        t = self._translation(lesson)
        return t.body if t else lesson.body

    def get_language(self, lesson):
        t = self._translation(lesson)
        return t.language if t else "en"

    def get_available_languages(self, lesson):
        return ["en"] + sorted(lesson.translations.values_list("language", flat=True))

    def get_unit(self, lesson):
        unit = lesson.unit
        return {
            "id": unit.id,
            "number": unit.number,
            "title": unit.localized_title(self.context.get("lang", "en")),
            "title_en": unit.title,
            "title_fr": unit.title_fr,
            "grade": unit.grade,
        }

    def get_subject(self, lesson):
        subject = lesson.unit.subject
        return {
            "code": subject.code,
            "name": subject.localized_name(self.context.get("lang", "en")),
            "icon": subject.icon,
            "color": subject.color,
        }

    def get_completed(self, lesson):
        user = self.context["request"].user
        return lesson.progress.filter(user=user).exists()


class LessonListSerializer(serializers.ModelSerializer):
    subject = serializers.SerializerMethodField()
    subject_code = serializers.CharField(source="unit.subject.code", read_only=True)
    grade = serializers.CharField(source="unit.grade", read_only=True)
    unit_title = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id",
            "slug",
            "title",
            "summary",
            "status",
            "is_free",
            "locked",
            "subject",
            "subject_code",
            "grade",
            "unit",
            "unit_title",
            "updated_at",
        ]

    def get_locked(self, lesson):
        return is_locked(self, lesson)

    def get_subject(self, lesson):
        return lesson.unit.subject.localized_name(serializer_language(self))

    def get_unit_title(self, lesson):
        return lesson.unit.localized_title(serializer_language(self))


class LessonTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonTranslation
        fields = ["language", "title", "summary", "body", "reviewed"]
        read_only_fields = ["reviewed"]


class LessonWriteSerializer(serializers.ModelSerializer):
    """Teachers author lessons; they go to review before students can see them."""

    translations = LessonTranslationSerializer(many=True, required=False)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "unit",
            "order",
            "slug",
            "title",
            "summary",
            "body",
            "video_url",
            "estimated_minutes",
            "status",
            "is_free",
            "simulations",
            "translations",
        ]
        read_only_fields = ["id"]

    def validate_status(self, value):
        user = self.context["request"].user
        if value == ContentStatus.PUBLISHED and not user.is_platform_admin:
            return ContentStatus.REVIEW
        return value

    def _save_translations(self, lesson, translations):
        for item in translations:
            if item["language"] == "en":
                continue
            LessonTranslation.objects.update_or_create(
                lesson=lesson,
                language=item["language"],
                defaults={"title": item["title"], "summary": item.get("summary", ""), "body": item["body"], "reviewed": False},
            )

    def create(self, validated_data):
        translations = validated_data.pop("translations", [])
        sims = validated_data.pop("simulations", [])
        lesson = Lesson.objects.create(**validated_data)
        lesson.simulations.set(sims)
        self._save_translations(lesson, translations)
        return lesson

    def update(self, instance, validated_data):
        translations = validated_data.pop("translations", None)
        lesson = super().update(instance, validated_data)
        if translations is not None:
            self._save_translations(lesson, translations)
        return lesson
