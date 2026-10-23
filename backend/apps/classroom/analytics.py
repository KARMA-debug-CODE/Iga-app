"""How a class is doing, unit by unit: shared by the gradebook (views.ClassroomViewSet.report) and Teaching Packs."""

from dataclasses import dataclass

from django.db.models import Sum

from apps.assessments.models import Answer, Attempt
from apps.curriculum.models import Unit


@dataclass(frozen=True)
class UnitScore:
    unit: Unit
    got: float
    possible: float

    @property
    def average(self):
        return round(self.got / self.possible * 100, 1)


def class_unit_scores(classroom, students, since=None):
    """Marks won out of marks possible per unit, from the marked answers of `students` (in the class's subject
    when it has one, and submitted from `since` when given). Weakest unit first; ties by unit id."""
    answers = Answer.objects.filter(
        attempt__user__in=students,
        attempt__status=Attempt.Status.MARKED,
        question__unit__isnull=False,
        marks_awarded__isnull=False,
    )
    if classroom.subject_id:
        answers = answers.filter(attempt__quiz__subject_id=classroom.subject_id)
    if since is not None:
        answers = answers.filter(attempt__submitted_at__gte=since)
    totals = answers.values("question__unit").annotate(got=Sum("marks_awarded"), possible=Sum("question__marks"))
    units = Unit.objects.in_bulk([row["question__unit"] for row in totals])
    scores = [
        UnitScore(units[row["question__unit"]], float(row["got"]), float(row["possible"])) for row in totals if row["possible"]
    ]
    return sorted(scores, key=lambda score: (score.average, score.unit.id))
