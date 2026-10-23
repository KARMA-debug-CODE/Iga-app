import copy

from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.core.text import clean_text

from .insight import students_needing_help
from .models import PLAN_EDITABLE_FIELDS, PackAssignment, TeachingPack

MAX_TEXT = 2000
STEP_FIELDS = {"teacher", "learners", "competences"}
MAX_STEPS = 3


def merged_document(pack):
    """The stored pack with the teacher's lesson-plan edits applied (step edits by position)."""
    document = copy.deepcopy(pack.document)
    plan = document.setdefault("plan", {})
    for key, value in (pack.plan_edits or {}).items():
        if key == "steps":
            steps = plan.get("steps", [])
            for index, edit in enumerate(value):
                if index < len(steps):
                    steps[index] = {**steps[index], **edit}
        else:
            plan[key] = value
    return document


class PackCreateSerializer(serializers.Serializer):
    classroom = serializers.IntegerField(min_value=1)
    unit = serializers.IntegerField(min_value=1)
    lesson = serializers.IntegerField(min_value=1, required=False, allow_null=True)


def _text(value):
    if not isinstance(value, str):
        raise serializers.ValidationError(_("Write plain text."))
    if len(value) > MAX_TEXT:
        raise serializers.ValidationError(_("Keep each field under %(count)s characters.") % {"count": MAX_TEXT})
    return clean_text(value, multiline=True)


class PlanEditSerializer(serializers.Serializer):
    """{plan: {field: text}}: only the lesson plan's editable fields, as plain text."""

    plan = serializers.DictField()

    def validate_plan(self, value):
        unknown = sorted(set(value) - set(PLAN_EDITABLE_FIELDS))
        if unknown:
            raise serializers.ValidationError(_("These fields can't be changed: %(fields)s.") % {"fields": ", ".join(unknown)})
        cleaned = {}
        for key, item in value.items():
            if key != "steps":
                cleaned[key] = _text(item)
                continue
            if not isinstance(item, list) or len(item) > MAX_STEPS:
                raise serializers.ValidationError(_("A lesson plan has at most %(count)s steps.") % {"count": MAX_STEPS})
            steps = []
            for step in item:
                if not isinstance(step, dict) or set(step) - STEP_FIELDS:
                    raise serializers.ValidationError(
                        _("A step can change only its teacher activities, learner activities and competences.")
                    )
                steps.append({field: _text(text) for field, text in step.items()})
            cleaned["steps"] = steps
        return cleaned


class PackSummarySerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(source="classroom.name", read_only=True)
    unit_label = serializers.SerializerMethodField()
    lesson_title = serializers.SerializerMethodField()

    class Meta:
        model = TeachingPack
        fields = ["id", "classroom", "classroom_name", "unit_label", "lesson_title", "created_at", "ai_used"]
        read_only_fields = fields

    def get_unit_label(self, pack):
        return (pack.document.get("unit") or {}).get("label", "")

    def get_lesson_title(self, pack):
        return (pack.document.get("lesson") or {}).get("title", "")


class PackSerializer(serializers.ModelSerializer):
    unit_id = serializers.IntegerField(read_only=True)
    lesson_id = serializers.IntegerField(read_only=True)
    document = serializers.SerializerMethodField()
    students_needing_help = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()

    class Meta:
        model = TeachingPack
        fields = [
            "id",
            "classroom",
            "unit_id",
            "lesson_id",
            "created_at",
            "language",
            "ai_used",
            "document",
            "students_needing_help",
            "assignments",
        ]
        read_only_fields = fields

    def get_document(self, pack):
        return merged_document(pack)

    def get_students_needing_help(self, pack):
        return students_needing_help(pack.classroom, pack.unit) if pack.unit_id else []

    def get_assignments(self, pack):
        return [{"what": a.what, "assignment_id": a.assignment_id, "quiz_id": a.quiz_id} for a in pack.assignments.all()]


class AssignSerializer(serializers.Serializer):
    what = serializers.ChoiceField(choices=PackAssignment.What.choices)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
