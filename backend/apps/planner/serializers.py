from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from .models import ExamDate, StudyPlan
from .services import MAX_WEEKLY_GOAL


class StudyPlanSerializer(serializers.ModelSerializer):
    weekly_goal_lessons = serializers.IntegerField(min_value=1, max_value=MAX_WEEKLY_GOAL)

    class Meta:
        model = StudyPlan
        fields = ["weekly_goal_lessons", "updated_at"]
        read_only_fields = ["updated_at"]


class ExamDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamDate
        fields = ["id", "title", "date", "created_at"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {"title": {"max_length": 120}}

    def validate_date(self, value):
        today = timezone.localdate()
        if value < today:
            raise serializers.ValidationError(_("Choose a date in the future."))
        if value > today + timedelta(days=366 * 6):
            raise serializers.ValidationError(_("That date is too far away."))
        return value

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError(_("Give the exam a name."))
        return value
