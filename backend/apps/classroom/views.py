from collections import defaultdict
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.serializers import PublicUserSerializer
from apps.assessments.models import Attempt
from apps.assessments.services import visible_quizzes
from apps.core import audit
from apps.core.permissions import IsTeacher
from apps.curriculum.models import LessonProgress
from apps.curriculum.views import visible_lessons
from apps.simulations.models import SimulationView

from .models import Assignment, Classroom, Enrollment


class ClassroomSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.display_name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True, default=None)
    subject_icon = serializers.CharField(source="subject.icon", read_only=True, default="🏫")
    student_count = serializers.SerializerMethodField()
    join_code = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = [
            "id",
            "name",
            "subject",
            "subject_name",
            "subject_icon",
            "grade",
            "teacher_name",
            "student_count",
            "join_code",
            "archived",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_student_count(self, classroom):
        return classroom.enrollments.count()

    def get_join_code(self, classroom):
        user = self.context["request"].user
        return classroom.join_code if classroom.teacher_id == user.id or user.is_platform_admin else None


class AssignmentSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)
    classroom_name = serializers.CharField(source="classroom.name", read_only=True)
    quiz_title = serializers.CharField(source="quiz.title", read_only=True, default=None)
    lesson_slug = serializers.CharField(source="lesson.slug", read_only=True, default=None)
    simulation_slug = serializers.CharField(source="simulation.slug", read_only=True, default=None)
    my_status = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            "id",
            "classroom",
            "classroom_name",
            "title",
            "instructions",
            "kind",
            "quiz",
            "quiz_title",
            "lesson",
            "lesson_slug",
            "simulation",
            "simulation_slug",
            "due_at",
            "created_at",
            "my_status",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        targets = [attrs.get(k) for k in ("quiz", "lesson", "simulation")]
        if sum(1 for t in targets if t) != 1:
            raise serializers.ValidationError("Attach exactly one quiz, lesson or simulation.")
        user = self.context["request"].user
        classroom = attrs.get("classroom")
        if classroom and classroom.teacher_id != user.id and not user.is_platform_admin:
            raise serializers.ValidationError({"classroom": "That is not your class."})
        if attrs.get("quiz") and not visible_quizzes(user).filter(pk=attrs["quiz"].pk).exists():
            raise serializers.ValidationError({"quiz": "Quiz not found."})
        if attrs.get("lesson") and not visible_lessons(user).filter(pk=attrs["lesson"].pk).exists():
            raise serializers.ValidationError({"lesson": "Lesson not found."})
        return attrs

    def get_my_status(self, assignment):
        user = self.context["request"].user
        if not user.is_student:
            return None
        return assignment_status(assignment, user)


def assignment_status(assignment, student):
    """'todo' | 'in_progress' | 'done' | 'needs_marking', plus a score for quizzes."""
    result = {"state": "todo", "score": None, "late": False}
    finished_at = None
    if assignment.quiz_id:
        attempts = Attempt.objects.filter(user=student, quiz_id=assignment.quiz_id, started_at__gte=assignment.created_at)
        finished = [a for a in attempts if a.status != Attempt.Status.IN_PROGRESS]
        if finished:
            best = max(finished, key=lambda a: a.percentage or 0)
            result["state"] = "needs_marking" if best.status == Attempt.Status.NEEDS_MARKING else "done"
            result["score"] = best.percentage
            finished_at = min(a.submitted_at for a in finished if a.submitted_at)
        elif attempts:
            result["state"] = "in_progress"
    elif assignment.lesson_id:
        progress = LessonProgress.objects.filter(user=student, lesson_id=assignment.lesson_id).first()
        if progress:
            result["state"] = "done"
            finished_at = progress.completed_at
    elif assignment.simulation_id:
        view = SimulationView.objects.filter(
            user=student, simulation_id=assignment.simulation_id, viewed_at__gte=assignment.created_at
        ).first()
        if view:
            result["state"] = "done"
            finished_at = view.viewed_at
    if assignment.due_at:
        if finished_at:
            result["late"] = finished_at > assignment.due_at
        else:
            result["late"] = timezone.now() > assignment.due_at
    return result


class ClassroomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassroomSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "report", "remove_student", "new_code"):
            return [IsTeacher()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Classroom.objects.select_related("teacher", "subject")
        if user.is_platform_admin:
            return qs
        if user.can_teach:
            return qs.filter(teacher=user)
        return qs.filter(enrollments__student=user, archived=False)

    def perform_create(self, serializer):
        classroom = serializer.save(teacher=self.request.user)
        audit.record(self.request, "create_class", classroom)

    def perform_destroy(self, instance):
        # Archive rather than delete so students' results are kept.
        instance.archived = True
        instance.save(update_fields=["archived"])
        audit.record(self.request, "archive_class", instance)

    def retrieve(self, request, *args, **kwargs):
        classroom = self.get_object()
        data = self.get_serializer(classroom).data
        data["assignments"] = AssignmentSerializer(
            classroom.assignments.select_related("quiz", "lesson", "simulation", "classroom"),
            many=True,
            context={"request": request},
        ).data
        if classroom.teacher_id == request.user.id or request.user.is_platform_admin:
            students = [e.student for e in classroom.enrollments.select_related("student").order_by("student__first_name")]
            data["students"] = PublicUserSerializer(students, many=True).data
        return Response(data)

    @action(detail=False, methods=["post"])
    def join(self, request):
        if not request.user.is_student:
            raise PermissionDenied("Only students join classes with a code.")
        code = (request.data.get("code") or "").strip().upper()
        classroom = Classroom.objects.filter(join_code=code, archived=False).first()
        if not classroom:
            raise ValidationError({"code": "No class has that code. Check with your teacher."})
        Enrollment.objects.get_or_create(classroom=classroom, student=request.user)
        return Response(self.get_serializer(classroom).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        classroom = self.get_object()
        Enrollment.objects.filter(classroom=classroom, student=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def remove_student(self, request, pk=None):
        classroom = self.get_object()
        deleted, _ = Enrollment.objects.filter(classroom=classroom, student_id=request.data.get("student")).delete()
        if not deleted:
            raise ValidationError({"student": "That student is not in this class."})
        audit.record(request, "remove_student", classroom, student=request.data.get("student"))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def new_code(self, request, pk=None):
        classroom = self.get_object()
        classroom.join_code = ""
        classroom.save()
        return Response({"join_code": classroom.join_code})

    @action(detail=True)
    def report(self, request, pk=None):
        """Gradebook: every student × every assignment, plus weakest units for the class."""
        classroom = self.get_object()
        students = [e.student for e in classroom.enrollments.select_related("student")]
        assignments = list(classroom.assignments.select_related("quiz", "lesson", "simulation"))

        rows = []
        for student in students:
            cells = {a.id: assignment_status(a, student) for a in assignments}
            scores = [c["score"] for c in cells.values() if c["score"] is not None]
            rows.append(
                {
                    "student": PublicUserSerializer(student).data,
                    "assignments": cells,
                    "completed": sum(1 for c in cells.values() if c["state"] in ("done", "needs_marking")),
                    "average_score": round(sum(scores) / len(scores), 1) if scores else None,
                    "lessons_completed": LessonProgress.objects.filter(user=student).count(),
                }
            )

        # Weak topics: average percentage per unit across all marked answers by class members.
        unit_totals = defaultdict(lambda: [0.0, 0.0, None])
        attempts = Attempt.objects.filter(user__in=students, status=Attempt.Status.MARKED).prefetch_related(
            "answers__question__unit"
        )
        if classroom.subject_id:
            attempts = attempts.filter(quiz__subject_id=classroom.subject_id)
        for attempt in attempts:
            for answer in attempt.answers.all():
                unit = answer.question.unit
                if unit is None or answer.marks_awarded is None:
                    continue
                totals = unit_totals[unit.id]
                totals[0] += float(answer.marks_awarded)
                totals[1] += float(answer.question.marks)
                totals[2] = unit
        weak_units = sorted(
            (
                {"unit": f"{u.grade} Unit {u.number}: {u.title}", "average": round(got / possible * 100, 1)}
                for got, possible, u in unit_totals.values()
                if possible
            ),
            key=lambda item: item["average"],
        )[:5]

        return Response(
            {
                "classroom": self.get_serializer(classroom).data,
                "assignments": [{"id": a.id, "title": a.title, "kind": a.kind, "due_at": a.due_at} for a in assignments],
                "rows": rows,
                "weak_units": weak_units,
            }
        )


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("create", "partial_update", "destroy"):
            return [IsTeacher()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Assignment.objects.select_related("classroom", "quiz", "lesson", "simulation")
        if user.is_platform_admin:
            pass
        elif user.can_teach:
            qs = qs.filter(classroom__teacher=user)
        else:
            qs = qs.filter(classroom__enrollments__student=user, classroom__archived=False)
        if self.request.query_params.get("classroom"):
            qs = qs.filter(classroom_id=self.request.query_params["classroom"])
        if self.request.query_params.get("upcoming"):
            qs = qs.filter(Q(due_at__isnull=True) | Q(due_at__gte=timezone.now() - timedelta(days=1)))
        return qs

    def perform_create(self, serializer):
        assignment = serializer.save(created_by=self.request.user)
        audit.record(self.request, "create_assignment", assignment, classroom=assignment.classroom_id)

    def perform_destroy(self, instance):
        audit.record(self.request, "delete_assignment", instance, title=instance.title)
        instance.delete()
