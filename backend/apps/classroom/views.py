from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.serializers import PublicUserSerializer
from apps.assessments.models import Attempt
from apps.assessments.services import finalize_if_expired, visible_quizzes
from apps.core import audit
from apps.core.permissions import IsTeacher
from apps.core.throttles import JoinRateThrottle
from apps.core.utils import serializer_language
from apps.core.validation import id_param, parse_id, text_field
from apps.curriculum.models import LessonProgress
from apps.curriculum.views import visible_lessons
from apps.schools import access
from apps.simulations.models import SimulationView

from . import roster
from .models import Assignment, Classroom, Enrollment


class ClassroomSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.display_name", read_only=True)
    subject_name = serializers.SerializerMethodField()
    subject_icon = serializers.CharField(source="subject.icon", read_only=True, default="school")
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
        return classroom.enrollments.filter(active=True).count()

    def get_subject_name(self, obj):
        return obj.subject.localized_name(serializer_language(self)) if obj.subject_id else None

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
    locked = serializers.SerializerMethodField()

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
            "locked",
        ]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {"instructions": {"max_length": 5000}}

    def validate(self, attrs):
        targets = [attrs.get(k) for k in ("quiz", "lesson", "simulation")]
        if sum(1 for t in targets if t) != 1:
            raise serializers.ValidationError(_("Attach exactly one quiz, lesson or simulation."))
        user = self.context["request"].user
        classroom = attrs.get("classroom")
        if classroom and classroom.teacher_id != user.id and not user.is_platform_admin:
            raise serializers.ValidationError({"classroom": _("That is not your class.")})
        if attrs.get("quiz") and not visible_quizzes(user).filter(pk=attrs["quiz"].pk).exists():
            raise serializers.ValidationError({"quiz": _("Quiz not found.")})
        if attrs.get("lesson") and not visible_lessons(user).filter(pk=attrs["lesson"].pk).exists():
            raise serializers.ValidationError({"lesson": _("Lesson not found.")})
        return attrs

    def get_my_status(self, assignment):
        user = self.context["request"].user
        if not user.is_student:
            return None
        return assignment_status(assignment, user)

    def get_locked(self, assignment):
        """True when the viewer can't open the assigned lesson or quiz (their school hasn't subscribed)."""
        target = assignment.quiz or assignment.lesson
        return target is not None and not access.can_open(self.context["request"].user, target)


class RosterImportSerializer(serializers.Serializer):
    # 200 rows (roster.MAX_ROWS) of names and emails fit easily.
    csv = serializers.CharField(max_length=100_000, allow_blank=True, required=False, default="", trim_whitespace=False)
    confirm = serializers.BooleanField(default=False)


def assignment_status(assignment, student):
    """'todo' | 'in_progress' | 'done' | 'needs_marking', plus a score for quizzes."""
    return assignment_statuses([assignment], [student])[(assignment.id, student.id)]


def assignment_statuses(assignments, students):
    """{(assignment_id, student_id): status} for a whole gradebook in a few queries."""
    student_ids = [s.id for s in students]
    quiz_ids = {a.quiz_id for a in assignments if a.quiz_id}
    lesson_ids = {a.lesson_id for a in assignments if a.lesson_id}
    sim_ids = {a.simulation_id for a in assignments if a.simulation_id}

    attempts = defaultdict(list)
    if quiz_ids:
        for attempt in Attempt.objects.filter(user_id__in=student_ids, quiz_id__in=quiz_ids):
            finalize_if_expired(attempt)  # time ran out but the student never came back
            attempts[(attempt.user_id, attempt.quiz_id)].append(attempt)
    completed = {}
    if lesson_ids:
        for row in LessonProgress.objects.filter(user_id__in=student_ids, lesson_id__in=lesson_ids):
            completed[(row.user_id, row.lesson_id)] = row.completed_at
    views = defaultdict(list)
    if sim_ids:
        for row in SimulationView.objects.filter(user_id__in=student_ids, simulation_id__in=sim_ids):
            views[(row.user_id, row.simulation_id)].append(row.viewed_at)

    result = {}
    for assignment in assignments:
        for sid in student_ids:
            status_ = {"state": "todo", "score": None, "late": False}
            finished_at = None
            if assignment.quiz_id:
                mine = [
                    a
                    for a in attempts[(sid, assignment.quiz_id)]
                    if a.started_at >= assignment.created_at or a.assignment_id == assignment.id
                ]
                finished = [a for a in mine if a.status != Attempt.Status.IN_PROGRESS and a.submitted_at]
                marked = [a for a in finished if a.status == Attempt.Status.MARKED]
                if marked:
                    # Best fully-marked score; on a tie, the earlier submission (so a late retake can't hide).
                    scored = max(marked, key=lambda a: (a.percentage or 0, -a.submitted_at.timestamp()))
                    status_.update(state="done", score=scored.percentage)
                    finished_at = scored.submitted_at
                elif finished:
                    status_["state"] = "needs_marking"
                    finished_at = min(a.submitted_at for a in finished)
                elif mine:
                    status_["state"] = "in_progress"
            elif assignment.lesson_id:
                finished_at = completed.get((sid, assignment.lesson_id))
                if finished_at:
                    status_["state"] = "done"
            elif assignment.simulation_id:
                seen = [t for t in views[(sid, assignment.simulation_id)] if t >= assignment.created_at]
                if seen:
                    status_["state"] = "done"
                    finished_at = min(seen)
            if assignment.due_at:
                status_["late"] = (finished_at or timezone.now()) > assignment.due_at
            result[(assignment.id, sid)] = status_
    return result


class ClassroomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassroomSerializer

    def get_permissions(self):
        if self.action in (
            "create",
            "update",
            "partial_update",
            "destroy",
            "report",
            "remove_student",
            "new_code",
            "import_roster",
            "reset_password",
        ):
            return [IsTeacher()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Classroom.objects.select_related("teacher", "subject")
        if user.is_platform_admin:
            return qs
        if user.can_teach:
            return qs.filter(teacher=user)
        if self.action == "list":
            # Classes for the student's grade; ?previous=1 lists the ones they had before moving grade.
            moved = self.request.query_params.get("previous") in ("1", "true")
            mine = qs.filter(enrollments__student=user, enrollments__active=not moved)
        else:
            mine = qs.filter(enrollments__student=user)
        # Students can still leave a class after it was archived.
        return mine if self.action == "leave" else mine.filter(archived=False)

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
            enrollments = classroom.enrollments.select_related("student").order_by("-active", "student__first_name")
            data["students"] = [
                {
                    **PublicUserSerializer(e.student).data,
                    "awaiting_first_login": e.student.must_change_password,
                    # Moved to another grade: kept here with their results, but the class left their lists.
                    "moved_to": "" if e.active else e.student.grade,
                }
                for e in enrollments
            ]
        elif request.user.is_student:
            # A class from before the student changed grade: still readable, but no longer counted.
            data["previous"] = not classroom.enrollments.filter(student=request.user, active=True).exists()
        return Response(data)

    @action(detail=False, methods=["post"], throttle_classes=[JoinRateThrottle])
    def join(self, request):
        if not request.user.is_student:
            raise PermissionDenied(_("Only students join classes with a code."))
        code = text_field(request.data, "code", 12).upper()
        classroom = Classroom.objects.filter(join_code=code, archived=False).first()
        if not classroom:
            raise ValidationError({"code": _("No class has that code. Check with your teacher.")})
        Enrollment.objects.update_or_create(classroom=classroom, student=request.user, defaults={"active": True, "left_at": None})
        return Response(self.get_serializer(classroom).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        classroom = self.get_object()
        Enrollment.objects.filter(classroom=classroom, student=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def remove_student(self, request, pk=None):
        classroom = self.get_object()
        student_id = parse_id(request.data.get("student"), "student")
        deleted, _created = Enrollment.objects.filter(classroom=classroom, student_id=student_id).delete()
        if not deleted:
            raise ValidationError({"student": _("That student is not in this class.")})
        audit.record(request, "remove_student", classroom, student=student_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def import_roster(self, request, pk=None):
        """Create student accounts from CSV text. {"csv": "...", "confirm": false} previews only."""
        classroom = self.get_object()
        if classroom.archived:
            raise ValidationError(_("This class is archived."))
        data = RosterImportSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            rows = roster.parse(data.validated_data["csv"])
        except roster.RosterError as exc:
            raise ValidationError({"csv": str(exc)})
        ok = roster.check(rows)
        if not ok or not data.validated_data["confirm"]:
            return Response({"valid": ok, "rows": rows})
        created = roster.create_accounts(rows, classroom, request.user)
        audit.record(request, "import_roster", classroom, count=len(created), usernames=[r["username"] for r in created])
        return Response({"valid": True, "created": created}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        """Give a student in this class a new temporary password (they choose their own at next login)."""
        classroom = self.get_object()
        student_id = parse_id(request.data.get("student"), "student")
        enrollment = (
            Enrollment.objects.filter(classroom=classroom, classroom__archived=False, student_id=student_id)
            .select_related("student")
            .first()
        )
        if enrollment is None or not enrollment.student.is_student:
            raise ValidationError({"student": _("That student is not in this class.")})
        password = roster.reset_password(enrollment.student)
        audit.record(request, "reset_student_password", enrollment.student, classroom=classroom.id)
        return Response({"username": enrollment.student.username, "temporary_password": password})

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
        enrollments = list(classroom.enrollments.select_related("student").order_by("-active"))
        students = [e.student for e in enrollments]
        moved = {e.student_id: e.student.grade for e in enrollments if not e.active}
        assignments = list(classroom.assignments.select_related("quiz", "lesson", "simulation"))

        statuses = assignment_statuses(assignments, students)
        lesson_counts = dict(
            LessonProgress.objects.filter(user__in=students).values("user").annotate(n=Count("id")).values_list("user", "n")
        )
        rows = []
        for student in students:
            cells = {a.id: statuses[(a.id, student.id)] for a in assignments}
            scores = [c["score"] for c in cells.values() if c["score"] is not None]
            rows.append(
                {
                    "student": PublicUserSerializer(student).data,
                    "assignments": cells,
                    "completed": sum(1 for c in cells.values() if c["state"] in ("done", "needs_marking")),
                    "average_score": round(sum(scores) / len(scores), 1) if scores else None,
                    "lessons_completed": lesson_counts.get(student.id, 0),
                    "moved_to": moved.get(student.id, ""),
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
            qs = qs.filter(classroom__enrollments__student=user, classroom__enrollments__active=True, classroom__archived=False)
        classroom_id = id_param(self.request, "classroom")
        if classroom_id:
            qs = qs.filter(classroom_id=classroom_id)
        if self.request.query_params.get("upcoming"):
            qs = qs.filter(Q(due_at__isnull=True) | Q(due_at__gte=timezone.now() - timedelta(days=1)))
        return qs

    def perform_create(self, serializer):
        assignment = serializer.save(created_by=self.request.user)
        audit.record(self.request, "create_assignment", assignment, classroom=assignment.classroom_id)

    def perform_destroy(self, instance):
        audit.record(self.request, "delete_assignment", instance, title=instance.title)
        instance.delete()
