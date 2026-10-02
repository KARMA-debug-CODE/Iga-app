import secrets
import string

from django.conf import settings
from django.db import models

from apps.core.constants import GRADES

# No 0/O or 1/I so codes are easy to read aloud and copy from a blackboard.
JOIN_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")


def generate_join_code(length=6):
    return "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(length))


class Classroom(models.Model):
    name = models.CharField(max_length=120)
    subject = models.ForeignKey("curriculum.Subject", null=True, blank=True, on_delete=models.SET_NULL, related_name="classrooms")
    grade = models.CharField(max_length=2, choices=GRADES)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="taught_classes")
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Enrollment", related_name="enrolled_classes", blank=True)
    join_code = models.CharField(max_length=8, unique=True, editable=False)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.grade})"

    def save(self, *args, **kwargs):
        if not self.join_code:
            code = generate_join_code()
            while Classroom.objects.filter(join_code=code).exists():
                code = generate_join_code()
            self.join_code = code
        super().save(*args, **kwargs)


class Enrollment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["classroom", "student"], name="unique_enrollment")]


class Assignment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    quiz = models.ForeignKey("assessments.Quiz", null=True, blank=True, on_delete=models.CASCADE, related_name="assignments")
    lesson = models.ForeignKey("curriculum.Lesson", null=True, blank=True, on_delete=models.CASCADE, related_name="assignments")
    simulation = models.ForeignKey(
        "simulations.Simulation", null=True, blank=True, on_delete=models.CASCADE, related_name="assignments"
    )
    due_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_at", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def kind(self):
        if self.quiz_id:
            return "quiz"
        if self.lesson_id:
            return "lesson"
        if self.simulation_id:
            return "simulation"
        return "task"
