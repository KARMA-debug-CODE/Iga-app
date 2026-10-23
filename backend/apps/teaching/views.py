"""Teaching Packs API (/api/teaching/): the class's own teacher makes, reads, edits, prints and assigns packs.
Making and assigning need the school's subscription; packs already made stay readable after it lapses."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.classroom.analytics import class_unit_scores
from apps.core.constants import ContentStatus
from apps.core.utils import request_language
from apps.curriculum.models import Unit

from .access import SubscriptionRequired, packs_for, require_active, require_premium, teacher_classroom
from .builder import apply_polish, build_pack, default_lesson
from .insight import current_students, students_answered, unit_insight, unit_label
from .models import TeachingPack
from .polish import polish
from .serializers import PackCreateSerializer, PackSerializer, PackSummarySerializer, PlanEditSerializer


def class_units(classroom):
    """The units a class can make packs for: its subject's (every subject's, without one) for its grade."""
    units = Unit.objects.filter(grade=classroom.grade).select_related("subject")
    if classroom.subject_id:
        units = units.filter(subject_id=classroom.subject_id)
    return units.order_by("subject__name", "number", "id")


class ClassUnitsView(APIView):
    """GET /api/teaching/classes/<id>/units/: the class's units, weakest first, with what Iga found. Free: it is
    the teaser an unpaid school sees (counts only, no question content)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        classroom = teacher_classroom(request.user, pk)
        lang = request_language(request)
        since = timezone.now() - timedelta(days=settings.TEACHING_LOOKBACK_DAYS)
        scores = {s.unit.id: s for s in class_unit_scores(classroom, current_students(classroom), since=since)}
        rows = []
        for unit in class_units(classroom):
            score = scores.get(unit.id)
            rows.append(
                {
                    "unit_id": unit.id,
                    "label": unit_label(unit, lang),
                    "subject": unit.subject.localized_name(lang),
                    "average": score.average if score else None,
                    "answered": students_answered(classroom, unit) if score else 0,
                    "misconceptions_found": len(unit_insight(classroom, unit, lang)["misconceptions"]) if score else 0,
                }
            )
        rows.sort(key=lambda row: (row["average"] is None, row["average"] or 0, row["unit_id"]))
        return Response(rows)


class PackViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        packs = packs_for(self.request.user).select_related("classroom", "unit").prefetch_related("assignments")
        if self.action == "list" and "classroom" in self.request.query_params:
            try:
                packs = packs.filter(classroom_id=int(self.request.query_params["classroom"]))
            except ValueError:
                raise ValidationError({"classroom": [_("Choose a class.")]}) from None
        return packs

    def get_serializer_class(self):
        return PackSummarySerializer if self.action == "list" else PackSerializer

    def get_throttles(self):
        # Making a pack reads the class's answers and may ask Santa: its own, tighter limit.
        if self.action == "create":
            self.throttle_scope = "teaching_pack"
        return super().get_throttles()

    def create(self, request):
        data = PackCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        classroom = teacher_classroom(request.user, data.validated_data["classroom"])
        require_active(classroom)
        unit = class_units(classroom).filter(pk=data.validated_data["unit"]).first()
        if unit is None:
            raise ValidationError({"unit": [_("Choose a unit of this class's subject and grade.")]})
        lesson_id = data.validated_data.get("lesson")
        if lesson_id:
            lesson = unit.lessons.filter(pk=lesson_id, status=ContentStatus.PUBLISHED).first()
            if lesson is None:
                raise ValidationError({"lesson": [_("Choose a published lesson of this unit.")]})
        else:
            lesson = default_lesson(unit)
        lang = request_language(request)
        try:
            require_premium(request.user)
        except SubscriptionRequired:
            # Unpaid: say what a pack would have found (counts only), so the school knows what it is missing.
            insight = unit_insight(classroom, unit, lang)
            teaser = {
                "unit": unit_label(unit, lang),
                "average": insight["average"],
                "misconceptions_found": len(insight["misconceptions"]),
            }
            require_premium(request.user, teaser)
        document = build_pack(classroom, unit, lesson, request.user, lang)
        suggestions = polish(document, request.user, lang)
        apply_polish(document, suggestions)
        pack = TeachingPack.objects.create(
            classroom=classroom,
            unit=unit,
            lesson=lesson,
            created_by=request.user,
            language=lang,
            document=document,
            ai_used=suggestions["ai"],
        )
        return Response(PackSerializer(pack, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        pack = self.get_object()
        data = PlanEditSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        edits = dict(pack.plan_edits or {})
        for key, value in data.validated_data["plan"].items():
            if key == "steps":
                steps = list(edits.get("steps", []))
                for index, step in enumerate(value):
                    while len(steps) <= index:
                        steps.append({})
                    steps[index] = {**steps[index], **step}
                edits["steps"] = steps
            else:
                edits[key] = value
        pack.plan_edits = edits
        pack.save(update_fields=["plan_edits"])
        return Response(PackSerializer(pack, context=self.get_serializer_context()).data)
