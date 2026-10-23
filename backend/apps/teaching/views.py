"""Teaching Packs API (/api/teaching/): the class's own teacher makes, reads, edits, prints and assigns packs.
Making and assigning need the school's subscription; packs already made stay readable after it lapses."""

from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assessments.models import Question, Quiz, QuizQuestion
from apps.classroom.analytics import class_unit_scores
from apps.classroom.models import Assignment
from apps.core.constants import ContentStatus
from apps.core.utils import request_language
from apps.curriculum.models import Unit

from .access import SubscriptionRequired, packs_for, require_active, require_premium, teacher_classroom
from .builder import LEVEL_NAMES, apply_polish, build_pack, default_lesson
from .insight import current_students, students_answered, unit_insight, unit_label
from .models import PackAssignment, TeachingPack
from .polish import polish
from .serializers import AssignSerializer, PackCreateSerializer, PackSerializer, PackSummarySerializer, PlanEditSerializer


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

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Assign the pack's quiz or one worksheet level to its class: a teacher-authored copy of the questions
        that are still published, as a practice quiz. Assigning the same part again returns the first one."""
        pack = self.get_object()
        data = AssignSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        what, due_at = data.validated_data["what"], data.validated_data.get("due_at")
        require_active(pack.classroom)
        require_premium(request.user)
        existing = _assigned_part(pack, what)
        if existing:
            return Response(_assignment_body(existing, dropped=0, created=False))
        ids = _part_question_ids(pack.document, what)
        published = Question.objects.filter(id__in=ids, status=ContentStatus.PUBLISHED).in_bulk()
        questions = [published[i] for i in ids if i in published]
        if not questions:
            return Response(
                {"detail": _("None of these questions can be assigned any more."), "code": "nothing_to_assign"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dropped = len(ids) - len(questions)
        try:
            with transaction.atomic():
                TeachingPack.objects.select_for_update().get(pk=pack.pk)  # one assign of this pack at a time
                existing = _assigned_part(pack, what)
                if existing:
                    return Response(_assignment_body(existing, dropped=0, created=False))
                row = _create_assignment(pack, what, questions, due_at, request.user)
        except IntegrityError:  # a simultaneous request created it first
            return Response(_assignment_body(_assigned_part(pack, what), dropped=0, created=False))
        return Response(_assignment_body(row, dropped=dropped, created=True), status=status.HTTP_201_CREATED)


def _part_question_ids(document, what):
    if what == PackAssignment.What.QUIZ:
        questions = document.get("quiz", {}).get("questions", [])
    else:
        questions = document.get("worksheet", {}).get(what.removeprefix("worksheet_"), [])
    return [q["id"] for q in questions]


def _assigned_part(pack, what):
    return PackAssignment.objects.filter(pack=pack, what=what, assignment__isnull=False).first()


def _part_title(pack, what):
    if what == PackAssignment.What.QUIZ:
        name = _("Diagnostic quiz") if pack.document.get("quiz", {}).get("diagnostic") else _("Targeted quiz")
    else:
        name = _("Worksheet: %(level)s") % {"level": LEVEL_NAMES[what.removeprefix("worksheet_")]}
    label = (pack.document.get("unit") or {}).get("label", "")
    return f"{label} - {name}"[:200] if label else name


def _create_assignment(pack, what, questions, due_at, teacher):
    first = questions[0]
    unit = pack.unit or first.unit
    title = _part_title(pack, what)
    quiz = Quiz.objects.create(
        title=title,
        subject=unit.subject if unit else first.subject,
        grade=unit.grade if unit else first.grade,
        unit=unit,
        status=ContentStatus.PUBLISHED,
        author=teacher,
        is_free=False,  # library questions stay premium, as in any teacher-made quiz
    )
    QuizQuestion.objects.bulk_create(QuizQuestion(quiz=quiz, question=q, order=i) for i, q in enumerate(questions))
    assignment = Assignment.objects.create(classroom=pack.classroom, title=title, quiz=quiz, due_at=due_at, created_by=teacher)
    row, _created = PackAssignment.objects.update_or_create(
        pack=pack, what=what, defaults={"quiz": quiz, "assignment": assignment}
    )
    return row


def _assignment_body(row, dropped, created):
    return {"what": row.what, "assignment_id": row.assignment_id, "quiz_id": row.quiz_id, "dropped": dropped, "created": created}
