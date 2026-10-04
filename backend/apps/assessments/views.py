from django.db.models import Count, Max, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.classroom.models import Assignment, Enrollment
from apps.core import audit
from apps.core.constants import ContentStatus
from apps.core.permissions import IsTeacher, IsTeacherOrReadOnly
from apps.schools import access

from . import services
from .analytics import quiz_analytics
from .models import Attempt, ExamPaper, Question, Quiz
from .serializers import (
    AnswerInputSerializer,
    AttemptListSerializer,
    AttemptSerializer,
    ExamPaperSerializer,
    MarkInputSerializer,
    QuestionSerializer,
    QuizSummarySerializer,
    QuizWriteSerializer,
)


class QuestionViewSet(viewsets.ModelViewSet):
    """The question bank. Teachers only — it contains the answers."""

    serializer_class = QuestionSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        user = self.request.user
        qs = Question.objects.select_related("subject").prefetch_related("choices")
        if not user.is_platform_admin:
            qs = qs.filter(Q(status=ContentStatus.PUBLISHED) | Q(author=user))
            if not access.has_premium(user):
                # Library questions (and their answers) are part of the subscription.
                qs = qs.exclude(services.library_questions_q())
        params = self.request.query_params
        for field, param in (
            ("subject__code", "subject"),
            ("grade", "grade"),
            ("unit_id", "unit"),
            ("type", "type"),
            ("source", "source"),
        ):
            if params.get(param):
                qs = qs.filter(**{field: params[param]})
        if params.get("mine"):
            qs = qs.filter(author=user)
        if params.get("q"):
            qs = qs.filter(prompt__icontains=params["q"])
        return qs

    def _check_owner(self, question):
        user = self.request.user
        if not user.is_platform_admin and question.author_id != user.id:
            raise PermissionDenied("You can only change questions you wrote.")

    def perform_create(self, serializer):
        question = serializer.save(author=self.request.user)
        audit.record(self.request, "create_question", question)

    def perform_update(self, serializer):
        self._check_owner(serializer.instance)
        question = serializer.save()
        audit.record(self.request, "update_question", question)

    def perform_destroy(self, instance):
        self._check_owner(instance)
        if instance.answers.exists():
            raise ValidationError("Students have already answered this question; archive the quiz instead.")
        audit.record(self.request, "delete_question", instance)
        instance.delete()


class QuizViewSet(viewsets.ModelViewSet):
    """Practice quizzes, class tests, mock exams and interactive past papers."""

    permission_classes = [IsTeacherOrReadOnly]

    def get_queryset(self):
        qs = (
            services.visible_quizzes(self.request.user)
            .select_related("subject", "exam_paper")
            .annotate(question_count=Count("quiz_questions", distinct=True), total_marks=Sum("quiz_questions__question__marks"))
            .order_by("subject__order", "grade", "title")
        )
        params = self.request.query_params
        for field, param in (("subject__code", "subject"), ("grade", "grade"), ("kind", "kind"), ("unit_id", "unit")):
            if params.get(param):
                qs = qs.filter(**{field: params[param]})
        if params.get("mine"):
            qs = qs.filter(author=self.request.user)
        if self.action == "list" and not params.get("mine") and not params.get("kind"):
            qs = qs.exclude(kind=Quiz.Kind.PAST_PAPER)  # past papers have their own library page
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return QuizWriteSerializer
        return QuizSummarySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            stats = (
                Attempt.objects.filter(user=self.request.user)
                .exclude(status=Attempt.Status.IN_PROGRESS)
                .values("quiz_id")
                .annotate(count=Count("id"), best=Max("score"))
            )
            context["attempt_stats"] = {row["quiz_id"]: {"count": row["count"], "best": row["best"]} for row in stats}
        return context

    def _set_free_flag(self, quiz):
        if not self.request.user.is_platform_admin:
            free = services.quiz_is_teacher_material(quiz)
            if quiz.is_free != free:
                quiz.is_free = free
                quiz.save(update_fields=["is_free"])

    def perform_create(self, serializer):
        user = self.request.user
        extra = {} if user.is_platform_admin else {"is_free": False}
        quiz = serializer.save(author=user, **extra)
        self._set_free_flag(quiz)
        audit.record(self.request, "create_quiz", quiz, status=quiz.status)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_platform_admin and serializer.instance.author_id != user.id:
            raise PermissionDenied("You can only edit quizzes you created.")
        quiz = serializer.instance
        if quiz.attempts.exists():
            if "question_ids" in serializer.validated_data and serializer.validated_data["question_ids"] != list(
                quiz.quiz_questions.order_by("order").values_list("question_id", flat=True)
            ):
                raise ValidationError({"question_ids": "Students have started this quiz; duplicate it to change the questions."})
            serializer.validated_data.pop("question_ids", None)
        extra = {}
        if not user.is_platform_admin and serializer.validated_data.get("status", quiz.status) not in (
            ContentStatus.DRAFT,
            ContentStatus.ARCHIVED,
        ):
            extra["status"] = ContentStatus.REVIEW  # like lessons: every teacher edit is re-reviewed
        if not user.is_platform_admin:
            serializer.validated_data.pop("is_free", None)
        quiz = serializer.save(**extra)
        self._set_free_flag(quiz)
        audit.record(self.request, "update_quiz", quiz, status=quiz.status)

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_platform_admin and instance.author_id != user.id:
            raise PermissionDenied("You can only delete quizzes you created.")
        if instance.attempts.exists():
            instance.status = ContentStatus.ARCHIVED
            instance.save(update_fields=["status"])
        else:
            instance.delete()
        audit.record(self.request, "delete_quiz", instance)

    @action(detail=True, permission_classes=[IsTeacher])
    def analytics(self, request, pk=None):
        """Item analysis for the teacher's students (optionally one class: ?classroom=<id>)."""
        quiz = self.get_object()
        # The analysis shows the answer key. Authors see their own free material; a quiz holding
        # library questions needs the subscription, even for the teacher who built it.
        if not (quiz.author_id == request.user.id and quiz.is_free):
            access.require(request.user, quiz)
        return Response(quiz_analytics(quiz, request.user, request.query_params.get("classroom")))

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def start(self, request, pk=None):
        quiz = self.get_object()
        if quiz.status == ContentStatus.ARCHIVED:
            raise ValidationError("This quiz is no longer available.")
        access.require(request.user, quiz)  # an assignment never grants access by itself
        assignment = None
        assignment_id = request.data.get("assignment")
        if assignment_id not in (None, ""):
            try:
                assignment_id = int(assignment_id)
            except (TypeError, ValueError):
                raise ValidationError({"assignment": "Unknown assignment."})
            assignment = get_object_or_404(
                Assignment.objects.distinct(),
                pk=assignment_id,
                quiz=quiz,
                classroom__archived=False,
                classroom__enrollments__student=request.user,
            )
        attempt = services.start_attempt(request.user, quiz, assignment)
        return Response(AttemptSerializer(attempt, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ExamPaperViewSet(viewsets.ReadOnlyModelViewSet):
    """Past national exam papers. Filters: ?level=O&year=2023&subject=mathematics&official=1"""

    serializer_class = ExamPaperSerializer

    def get_queryset(self):
        qs = ExamPaper.objects.select_related("subject", "quiz")
        params = self.request.query_params
        for field, param in (("level", "level"), ("year", "year"), ("subject__code", "subject")):
            if params.get(param):
                qs = qs.filter(**{field: params[param]})
        if params.get("official") in ("1", "true"):
            qs = qs.filter(is_official=True)
        return qs

    @action(detail=False)
    def years(self, request):
        return Response(sorted(set(ExamPaper.objects.values_list("year", flat=True)), reverse=True))


def attempts_visible_to(user):
    qs = Attempt.objects.select_related("quiz", "quiz__subject", "user")
    if user.is_platform_admin:
        return qs
    if user.can_teach:
        my_students = Enrollment.objects.filter(classroom__teacher=user, classroom__archived=False).values("student_id")
        return qs.filter(Q(user=user) | Q(user_id__in=my_students))
    return qs.filter(user=user)


class AttemptViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    def get_queryset(self):
        qs = attempts_visible_to(self.request.user)
        if self.action == "list":
            qs = qs.filter(user=self.request.user)
            if self.request.query_params.get("quiz"):
                qs = qs.filter(quiz_id=self.request.query_params["quiz"])
        return qs

    def get_serializer_class(self):
        return AttemptListSerializer if self.action == "list" else AttemptSerializer

    def get_object(self):
        attempt = super().get_object()
        services.finalize_if_expired(attempt)
        user = self.request.user
        if (
            attempt.status == Attempt.Status.IN_PROGRESS
            and attempt.user_id == user.id
            and not access.can_open(user, attempt.quiz)
        ):
            # Access ended (e.g. the subscription lapsed) mid-attempt: close it with what was
            # answered, so it can't be kept open to read the questions.
            attempt = services.submit_attempt(attempt)
        return attempt

    def _own_attempt(self, needs_access=True):
        attempt = self.get_object()
        if attempt.user_id != self.request.user.id:
            raise PermissionDenied("This is not your attempt.")
        if needs_access and attempt.status == Attempt.Status.IN_PROGRESS:
            access.require(self.request.user, attempt.quiz)
        return attempt

    @action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        attempt = self._own_attempt()
        data = AnswerInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        services.save_answer(attempt, v["question"], v["choice_ids"], v["text"], v["numeric"])
        return Response({"saved": True})

    @action(detail=True, methods=["post"])
    def check(self, request, pk=None):
        attempt = self._own_attempt()
        question_id = request.data.get("question")
        services.check_answer(attempt, question_id)
        attempt.refresh_from_db()
        payload = AttemptSerializer(attempt, context={"request": request}).data
        question = next((q for q in payload["questions"] if q["id"] == int(question_id)), None)
        return Response(question)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        attempt = self._own_attempt(needs_access=False)  # finishing is always allowed
        attempt = services.submit_attempt(attempt)
        return Response(AttemptSerializer(attempt, context={"request": request}).data)


class MarkingViewSet(viewsets.ViewSet):
    """Teacher queue of written answers waiting for marks."""

    permission_classes = [IsTeacher]

    def _answers(self, request):
        return services.markable_answers(request.user).select_related(
            "question", "attempt", "attempt__user", "attempt__quiz", "attempt__quiz__subject"
        )

    def list(self, request):
        pending = self._answers(request).filter(marks_awarded__isnull=True).order_by("attempt__submitted_at")[:200]
        return Response(
            [
                {
                    "id": a.id,
                    "student": a.attempt.user.display_name,
                    "quiz": a.attempt.quiz.title,
                    "subject": a.attempt.quiz.subject.name,
                    "submitted_at": a.attempt.submitted_at,
                    "question": a.question.prompt,
                    "max_marks": a.question.marks,
                    # Marking guides are premium, like the explanations students see.
                    "marking_guide": a.question.marking_guide if access.can_open(request.user, a.attempt.quiz) else "",
                    "answer_text": a.text_answer,
                }
                for a in pending
            ]
        )

    @action(detail=True, methods=["post"])
    def mark(self, request, pk=None):
        answer = get_object_or_404(self._answers(request), pk=pk)
        data = MarkInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.mark_answer(answer, data.validated_data["marks"], data.validated_data["feedback"], request.user)
        audit.record(request, "mark_answer", answer, marks=str(answer.marks_awarded), student=answer.attempt.user_id)
        return Response({"id": answer.id, "marks_awarded": answer.marks_awarded, "attempt_status": answer.attempt.status})
