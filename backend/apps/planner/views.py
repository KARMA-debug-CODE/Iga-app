from django.utils.translation import gettext as _
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.utils import request_language

from . import services
from .models import ExamDate, StudyPlan
from .serializers import ExamDateSerializer, StudyPlanSerializer


class StudyPlanView(APIView):
    """The student's own weekly goal, plus the dashboard summary. Scoped to the signed-in user only."""

    permission_classes = [IsAuthenticated]

    def _data(self, request):
        plan = services.get_plan(request.user)
        return {
            "weekly_goal_lessons": plan.weekly_goal_lessons if plan else services.DEFAULT_WEEKLY_GOAL,
            "has_plan": plan is not None,
            "exams": ExamDateSerializer(request.user.exam_dates.all(), many=True).data,
            "summary": services.dashboard_summary(request.user, request_language(request)),
        }

    def get(self, request):
        return Response(self._data(request))

    def put(self, request):
        serializer = StudyPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        StudyPlan.objects.update_or_create(
            user=request.user, defaults={"weekly_goal_lessons": serializer.validated_data["weekly_goal_lessons"]}
        )
        return Response(self._data(request))


class ExamDateViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """A student's exam dates. Every row belongs to the signed-in user; nobody else's is ever touched."""

    serializer_class = ExamDateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExamDate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if self.get_queryset().count() >= services.MAX_EXAM_DATES:
            raise ValidationError(_("You can track up to %(n)s exam dates.") % {"n": services.MAX_EXAM_DATES})
        serializer.save(user=self.request.user)
