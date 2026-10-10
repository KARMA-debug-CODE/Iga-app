from collections import defaultdict

from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.assessments.services import visible_quizzes
from apps.core import audit
from apps.core.constants import ContentStatus
from apps.core.permissions import IsTeacherOrReadOnly
from apps.core.utils import request_grade, request_language
from apps.gamification import services as gamification
from apps.schools.access import content_access, has_premium, require

from .models import Lesson, LessonProgress, LessonTranslation, Resource, Subject, Unit
from .serializers import (
    LessonDetailSerializer,
    LessonListSerializer,
    LessonWriteSerializer,
    ResourceSerializer,
    SubjectSerializer,
    UnitSerializer,
)


def visible_lessons(user):
    qs = Lesson.objects.all()
    if user.is_platform_admin:
        return qs
    rule = Q(status=ContentStatus.PUBLISHED)
    if user.can_teach:
        rule |= Q(author=user)
    else:
        assigned_ids = Lesson.objects.filter(
            assignments__classroom__enrollments__student=user, assignments__classroom__enrollments__active=True
        ).values("id")
        rule |= Q(id__in=assigned_ids)
    return qs.filter(rule)


def _count_per_subject(qs, subject_path):
    counts = qs.filter(**{subject_path: OuterRef("pk")}).order_by().values(subject_path).annotate(n=Count("pk")).values("n")
    return Coalesce(Subquery(counts[:1], output_field=IntegerField()), 0)


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    """Subjects with the current user's progress. `?grade=S3` filters to one grade."""

    serializer_class = SubjectSerializer
    lookup_field = "code"
    pagination_class = None

    def get_queryset(self):
        grade = request_grade(self.request)
        user = self.request.user
        qs = Subject.objects.all()
        if self.action == "retrieve":
            return qs  # opening a subject directly works whatever the grade filter
        units = Unit.objects.all()
        lessons = visible_lessons(user)
        progress = LessonProgress.objects.filter(user=user, lesson__in=visible_lessons(user).values("id"))
        if grade:
            qs = qs.filter(offered_o_level=True) if grade in ("S1", "S2", "S3") else qs.filter(offered_a_level=True)
            units = units.filter(grade=grade)
            lessons = lessons.filter(unit__grade=grade)
            progress = progress.filter(lesson__unit__grade=grade)
        # Separate counting subqueries: one join across units, lessons and progress multiplies rows.
        return qs.annotate(
            unit_count=_count_per_subject(units, "subject"),
            lesson_count=_count_per_subject(lessons, "unit__subject"),
            completed_count=_count_per_subject(progress, "lesson__unit__subject"),
        )

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "lang": request_language(self.request)}

    def retrieve(self, request, *args, **kwargs):
        subject = self.get_object()
        grade = request.query_params.get("grade")
        units = subject.units.all()
        if grade:
            units = units.filter(grade=grade)
        units = list(units)

        lessons = list(visible_lessons(request.user).filter(unit__in=units).order_by("order"))
        lessons_by_unit = defaultdict(list)
        for lesson in lessons:
            lessons_by_unit[lesson.unit_id].append(lesson)
        lang = request_language(request)
        translations = {t.lesson_id: t for t in LessonTranslation.objects.filter(lesson__in=lessons, language=lang)}
        completed_ids = set(
            LessonProgress.objects.filter(user=request.user, lesson__in=lessons).values_list("lesson_id", flat=True)
        )
        context = {
            **self.get_serializer_context(),
            "lessons_by_unit": lessons_by_unit,
            "translations": translations,
            "completed_ids": completed_ids,
        }
        data = SubjectSerializer(subject, context=context).data
        data["units"] = UnitSerializer(units, many=True, context=context).data
        data.update(unit_count=len(units), lesson_count=len(lessons), completed_count=len(completed_ids))
        data["grades"] = sorted(set(subject.units.values_list("grade", flat=True)))
        return Response(data)


class LessonViewSet(
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "slug"
    permission_classes = [IsTeacherOrReadOnly]

    def get_queryset(self):
        qs = visible_lessons(self.request.user).select_related("unit", "unit__subject", "author")
        params = self.request.query_params
        if params.get("unit"):
            qs = qs.filter(unit_id=params["unit"])
        if params.get("subject"):
            qs = qs.filter(unit__subject__code=params["subject"])
        if params.get("grade"):
            qs = qs.filter(unit__grade=params["grade"])
        if params.get("mine") and self.request.user.can_teach:
            qs = qs.filter(author=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LessonWriteSerializer
        if self.action == "list":
            return LessonListSerializer
        return LessonDetailSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "lang": request_language(self.request)}

    def retrieve(self, request, *args, **kwargs):
        lesson = self.get_object()
        data = self.get_serializer(lesson).data
        lang = request_language(request)

        siblings = list(visible_lessons(request.user).filter(unit=lesson.unit).order_by("order").values("id", "slug", "title"))
        if lang != "en":
            titles = dict(
                LessonTranslation.objects.filter(lesson_id__in=[s["id"] for s in siblings], language=lang).values_list(
                    "lesson_id", "title"
                )
            )
            for sibling in siblings:
                sibling["title"] = titles.get(sibling["id"], sibling["title"])
        for sibling in siblings:
            del sibling["id"]
        index = next((i for i, s in enumerate(siblings) if s["slug"] == lesson.slug), None)
        data["previous"] = siblings[index - 1] if index else None
        data["next"] = siblings[index + 1] if index is not None and index + 1 < len(siblings) else None

        data["simulations"] = [
            {
                "slug": sim.slug,
                "title": (sim.title_fr if lang == "fr" else "") or sim.title,
                "provider": sim.provider,
                "provider_id": sim.provider_id,
                "embed_url": sim.embed_url(lang),
            }
            for sim in lesson.simulations.all()
        ]
        data["resources"] = ResourceSerializer(
            Resource.objects.filter(status=ContentStatus.PUBLISHED)
            .filter(Q(unit=lesson.unit) | Q(unit__isnull=True, subject=lesson.unit.subject, grade=lesson.unit.grade))
            .order_by("-is_official", "kind", "title"),
            many=True,
            context={"request": request},
        ).data
        premium = has_premium(request.user)
        data["quizzes"] = [
            {
                "id": q.id,
                "title": q.title,
                "kind": q.kind,
                "question_count": q.quiz_questions.count(),
                "locked": not (q.is_free or premium),
            }
            for q in visible_quizzes(request.user).filter(unit=lesson.unit)
        ]
        if data["locked"]:
            data["access_reason"] = content_access(request.user).reason
        return Response(data)

    def perform_create(self, serializer):
        user = self.request.user
        status_value = serializer.validated_data.get("status", ContentStatus.REVIEW)
        extra = {} if user.is_platform_admin else {"is_free": True}  # a teacher's own material stays open
        lesson = serializer.save(author=user, status=status_value, **extra)
        audit.record(self.request, "create_lesson", lesson, status=lesson.status)

    def perform_update(self, serializer):
        user = self.request.user
        lesson = serializer.instance
        if not user.is_platform_admin and lesson.author_id != user.id:
            raise PermissionDenied(_("You can only edit lessons you wrote."))
        extra = {}
        if not user.is_platform_admin:
            extra["is_free"] = True
            if serializer.validated_data.get("status") != ContentStatus.DRAFT:
                extra["status"] = ContentStatus.REVIEW  # every teacher edit is re-reviewed
        lesson = serializer.save(**extra)
        audit.record(self.request, "update_lesson", lesson, status=lesson.status)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def complete(self, request, slug=None):
        lesson = self.get_object()
        require(request.user, lesson)  # no XP for lessons the student can't open
        _obj, created = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
        xp = gamification.on_lesson_completed(request.user, lesson) if created else 0
        return Response({"completed": True, "xp_gained": xp, "xp": request.user.xp}, status=status.HTTP_200_OK)


class ResourceViewSet(viewsets.ModelViewSet):
    serializer_class = ResourceSerializer
    permission_classes = [IsTeacherOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = Resource.objects.select_related("subject")
        if not user.is_platform_admin:
            qs = qs.filter(Q(status=ContentStatus.PUBLISHED) | Q(uploaded_by=user))
        params = self.request.query_params
        for field, param in (("subject__code", "subject"), ("grade", "grade"), ("kind", "kind"), ("unit_id", "unit")):
            if params.get(param):
                qs = qs.filter(**{field: params[param]})
        if params.get("official") in ("1", "true"):
            qs = qs.filter(is_official=True)
        return qs.order_by("-is_official", "kind", "title")

    def perform_create(self, serializer):
        user = self.request.user
        resource = serializer.save(
            uploaded_by=user,
            status=ContentStatus.PUBLISHED if user.is_platform_admin else ContentStatus.REVIEW,
        )
        audit.record(self.request, "create_resource", resource)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_platform_admin and serializer.instance.uploaded_by_id != user.id:
            raise PermissionDenied(_("You can only edit resources you uploaded."))
        resource = serializer.save(status=serializer.instance.status if user.is_platform_admin else ContentStatus.REVIEW)
        audit.record(self.request, "update_resource", resource)

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_platform_admin and instance.uploaded_by_id != user.id:
            raise PermissionDenied(_("You can only delete resources you uploaded."))
        audit.record(self.request, "delete_resource", instance, title=instance.title)
        instance.delete()


class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    """Flat list of units, used by teacher tools to pick where content belongs."""

    queryset = Unit.objects.select_related("subject")
    serializer_class = UnitSerializer
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get("subject"):
            qs = qs.filter(subject__code=params["subject"])
        if params.get("grade"):
            qs = qs.filter(grade=params["grade"])
        return qs

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "lessons_by_unit": {}}
