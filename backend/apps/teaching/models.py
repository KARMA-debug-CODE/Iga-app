"""Teaching Packs: what a class gets wrong in a unit, turned into a lesson plan, a worksheet and a quiz.

A pack is a snapshot (`document`, built by builder.build_pack) so a reprint is identical even after new results
arrive; the teacher's changes to the lesson plan are kept apart in `plan_edits`. See
docs/superpowers/specs/2026-10-23-teaching-packs-design.md."""

from django.conf import settings
from django.db import models

# The lesson-plan fields a teacher may change (PATCH /api/teaching/packs/<id>/). Everything else is read-only.
PLAN_EDITABLE_FIELDS = (
    "school",
    "teacher",
    "term",
    "date",
    "lesson_number",
    "duration",
    "class_size",
    "sen_learners",
    "unit_title",
    "key_unit_competence",
    "lesson_title",
    "objective",
    "location",
    "materials",
    "references",
    "steps",
    "evaluation",
    "self_evaluation",
)


class TeachingPack(models.Model):
    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        FRENCH = "fr", "French"

    classroom = models.ForeignKey("classroom.Classroom", on_delete=models.CASCADE, related_name="teaching_packs")
    unit = models.ForeignKey("curriculum.Unit", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    lesson = models.ForeignKey("curriculum.Lesson", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teaching_packs")
    created_at = models.DateTimeField(auto_now_add=True)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.ENGLISH)
    document = models.JSONField(help_text="The pack as built (builder.build_pack): read-only")
    plan_edits = models.JSONField(default=dict, blank=True, help_text="The teacher's changes to the lesson plan")
    ai_used = models.BooleanField(default=False, help_text="Santa wrote the hook and the simpler explanation")

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.document.get('unit', {}).get('label', 'Teaching pack')} ({self.classroom})"


class PackAssignment(models.Model):
    """A part of a pack assigned to its class in Iga: the quiz, or one worksheet level."""

    class What(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        WORKSHEET_SUPPORT = "worksheet_support", "Worksheet: support"
        WORKSHEET_CORE = "worksheet_core", "Worksheet: core"
        WORKSHEET_STRETCH = "worksheet_stretch", "Worksheet: stretch"

    pack = models.ForeignKey(TeachingPack, on_delete=models.CASCADE, related_name="assignments")
    what = models.CharField(max_length=20, choices=What.choices)
    quiz = models.ForeignKey("assessments.Quiz", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    assignment = models.ForeignKey("classroom.Assignment", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["pack", "what"], name="one_assignment_per_pack_part")]
