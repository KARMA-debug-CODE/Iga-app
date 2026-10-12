from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.assessments.models import Attempt, Question, Quiz
from apps.assessments.serializers import AttemptListSerializer
from apps.assessments.services import attempts_visible_to, markable_answers, visible_quizzes
from apps.classroom.models import Assignment, Classroom
from apps.classroom.views import AssignmentSerializer, assignment_statuses
from apps.core.serializers import SaveChangedFieldsMixin
from apps.core.utils import request_language
from apps.curriculum.models import Lesson, LessonProgress, Resource, Subject, localized_lesson_titles
from apps.curriculum.views import visible_lessons
from apps.schools.access import has_premium
from apps.schools.views import revenue_summary
from apps.simulations.models import Simulation, SimulationView

from . import admin_login, audit
from .constants import GRADES, LANGUAGES, ContentStatus
from .models import AuditLog
from .permissions import IsPlatformAdmin, RecentAuthentication

User = get_user_model()


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def meta(request):
    return Response(
        {
            "app_name": settings.APP_NAME,
            "grades": [{"code": c, "name": n} for c, n in GRADES],
            "languages": [{"code": c, "name": n} for c, n in LANGUAGES],
            "subjects": [
                {
                    "code": s.code,
                    "name": s.localized_name(request_language(request)),
                    "icon": s.icon,
                    "offered_o_level": s.offered_o_level,
                    "offered_a_level": s.offered_a_level,
                }
                for s in Subject.objects.all()
            ],
        }
    )


def level_from_xp(xp):
    """Every level needs 100 XP more than the last: 0, 100, 300, 600, ..."""
    level, needed, floor = 1, 100, 0
    while xp >= floor + needed:
        floor += needed
        level += 1
        needed += 100
    return {"level": level, "current": xp - floor, "needed": needed}


def _continue_learning(user, lang="en"):
    last = LessonProgress.objects.filter(user=user).select_related("lesson__unit").order_by("-completed_at").first()
    done = LessonProgress.objects.filter(user=user).values("lesson_id")
    lessons = (
        visible_lessons(user).filter(status=ContentStatus.PUBLISHED).exclude(id__in=done).select_related("unit", "unit__subject")
    )
    candidate = None
    if not has_premium(user):
        lessons = lessons.filter(is_free=True)  # suggest something the student can actually open
    if last and (not user.grade or last.lesson.unit.grade == user.grade):
        # Carry on in the same subject, unless the student has since moved to another grade.
        unit = last.lesson.unit
        candidate = lessons.filter(unit__subject=unit.subject, unit__grade=unit.grade).order_by("unit__number", "order").first()
    if candidate is None and user.grade:
        in_grade = lessons.filter(unit__grade=user.grade).order_by("unit__subject__order", "unit__number", "order")
        if user.combination_subjects:  # an A-level student starts with a subject of their combination
            candidate = in_grade.filter(unit__subject__code__in=user.combination_subjects).first()
        candidate = candidate or in_grade.first()
    if candidate is None and not user.grade:
        candidate = lessons.order_by("unit__grade", "unit__subject__order", "unit__number", "order").first()
    if candidate is None:
        return None
    translation = candidate.translations.filter(language=lang).first() if lang != "en" else None
    return {
        "slug": candidate.slug,
        "title": translation.title if translation else candidate.title,
        "subject": candidate.unit.subject.localized_name(lang),
        "icon": candidate.unit.subject.icon,
        "unit_number": candidate.unit.number,
        "unit_title": candidate.unit.localized_title(lang),
    }


@api_view(["GET"])
def dashboard(request):
    user = request.user
    data = {"level": level_from_xp(user.xp), "xp": user.xp, "streak_days": user.current_streak}

    if user.can_teach:
        classes = Classroom.objects.filter(teacher=user, archived=False).annotate(
            student_total=Count("enrollments", filter=Q(enrollments__active=True))
        )
        data["teacher"] = {
            "classes": [
                {"id": c.id, "name": c.name, "grade": c.grade, "students": c.student_total, "join_code": c.join_code}
                for c in classes
            ],
            "pending_marking": markable_answers(user).filter(marks_awarded__isnull=True).count(),
            "recent_submissions": AttemptListSerializer(
                attempts_visible_to(user)
                .exclude(user=user)
                .exclude(status=Attempt.Status.IN_PROGRESS)
                .order_by("-submitted_at")[:8],
                many=True,
                context={"request": request},
            ).data,
            "awaiting_review": {
                "lessons": Lesson.objects.filter(author=user, status=ContentStatus.REVIEW).count(),
                "quizzes": Quiz.objects.filter(author=user, status=ContentStatus.REVIEW).count(),
            },
            "approved": user.teacher_approved or user.is_platform_admin,
        }
        return Response(data)

    if user.is_teacher and not user.teacher_approved:
        data["teacher"] = {"approved": False}

    # Work out what is still to do first, then take the soonest six (not the other way round,
    # or six finished assignments could hide an unfinished one).
    candidates = list(
        Assignment.objects.filter(
            classroom__enrollments__student=user, classroom__enrollments__active=True, classroom__archived=False
        )
        .filter(Q(due_at__isnull=True) | Q(due_at__gte=timezone.now() - timedelta(days=7)))
        .select_related("classroom", "quiz", "lesson", "simulation")
        .order_by(F("due_at").asc(nulls_last=True), "-created_at")[:200]
    )
    statuses = assignment_statuses(candidates, [user])
    open_ones = [a for a in candidates if statuses[(a.id, user.id)]["state"] in ("todo", "in_progress")][:6]
    data["assignments"] = AssignmentSerializer(open_ones, many=True, context={"request": request}).data
    data["recent_attempts"] = AttemptListSerializer(
        Attempt.objects.filter(user=user)
        .exclude(status=Attempt.Status.IN_PROGRESS)
        .select_related("quiz", "quiz__subject")
        .order_by("-submitted_at")[:5],
        many=True,
        context={"request": request},
    ).data
    data["continue_learning"] = _continue_learning(user, request_language(request))
    data["lessons_completed"] = LessonProgress.objects.filter(user=user).count()
    data["badges_earned"] = user.badges.count()
    return Response(data)


@api_view(["GET"])
def search(request):
    term = (request.query_params.get("q") or "").strip()
    if len(term) < 2:
        return Response({"lessons": [], "simulations": [], "quizzes": [], "subjects": []})
    user = request.user
    lang = request_language(request)
    premium = has_premium(user)
    # Without a subscription, premium lesson text isn't searchable (it would reveal what's inside).
    free_only = {} if premium else {"is_free": True}
    match = Q(title__icontains=term) | Q(summary__icontains=term) | Q(body__icontains=term, **free_only)
    if lang != "en":
        # French readers search the French text too (titles, summaries, and bodies under the same rule).
        translated = Q(translations__language=lang) & (
            Q(translations__title__icontains=term)
            | Q(translations__summary__icontains=term)
            | Q(translations__body__icontains=term, **free_only)
        )
        match |= translated
    lessons = list(visible_lessons(user).filter(match).distinct().select_related("unit", "unit__subject")[:10])
    titles = localized_lesson_titles(lessons, lang)
    sim_match = Q(title__icontains=term) | Q(topics__icontains=term)
    if lang == "fr":
        sim_match |= Q(title_fr__icontains=term)
    sims = Simulation.objects.filter(sim_match)[:8]
    quizzes = visible_quizzes(user).filter(title__icontains=term).select_related("subject")[:8]
    subjects = Subject.objects.filter(Q(name__icontains=term) | Q(name_fr__icontains=term))[:5]
    return Response(
        {
            "lessons": [
                {
                    "slug": les.slug,
                    "title": titles[les.id],
                    "subject": les.unit.subject.localized_name(lang),
                    "grade": les.unit.grade,
                    "icon": les.unit.subject.icon,
                    "locked": not (les.is_free or premium),
                }
                for les in lessons
            ],
            "simulations": [
                {"slug": s.slug, "title": (s.title_fr if lang == "fr" else "") or s.title, "provider": s.provider} for s in sims
            ],
            "quizzes": [
                {
                    "id": q.id,
                    "title": q.title,
                    "kind": q.kind,
                    "subject": q.subject.localized_name(lang),
                    "locked": not (q.is_free or premium),
                }
                for q in quizzes
            ],
            "subjects": [{"code": s.code, "name": s.localized_name(lang), "icon": s.icon} for s in subjects],
        }
    )


# --- Administration ------------------------------------------------------------


class AdminUserSerializer(SaveChangedFieldsMixin, serializers.ModelSerializer):
    school = serializers.CharField(source="school.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "teacher_approved",
            "grade",
            "school",
            "school_status",
            "is_active",
            "xp",
            "last_login",
            "date_joined",
        ]
        read_only_fields = ["id", "username", "email", "school_status", "xp", "last_login", "date_joined"]


class AdminUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsPlatformAdmin, RecentAuthentication]
    serializer_class = AdminUserSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        qs = User.objects.order_by("-date_joined")
        params = self.request.query_params
        if params.get("role"):
            qs = qs.filter(role=params["role"])
        if params.get("pending_teachers"):
            qs = qs.filter(role=User.Role.TEACHER, teacher_approved=False)
        if params.get("q"):
            term = params["q"]
            qs = qs.filter(
                Q(username__icontains=term)
                | Q(email__icontains=term)
                | Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
            )
        return qs

    def list(self, request, *args, **kwargs):
        # The user directory holds everyone's email address: each look at it is recorded.
        filters = {
            k: request.query_params[k][:100] for k in ("role", "pending_teachers", "q", "page") if k in request.query_params
        }
        audit.record(request, "list_users", request.user, **filters)
        return super().list(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        # Role and approval changes happen one at a time per user, on the row as it is now.
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    def get_object(self):
        user = super().get_object()
        if self.action in ("update", "partial_update"):
            user = User.objects.select_for_update().get(pk=user.pk)
        return user

    def perform_update(self, serializer):
        before = {f: getattr(serializer.instance, f) for f in ("role", "teacher_approved", "is_active")}
        if serializer.instance == self.request.user and serializer.validated_data.get("role", "admin") != "admin":
            raise ValidationError(_("You can't remove your own administrator role."))
        user = serializer.save()
        if before["teacher_approved"] != user.teacher_approved:
            # The Iga team's decision replaces any school's, and a withdrawal sticks.
            user.set_teacher_approval(user.teacher_approved)
            user.save(update_fields=["teacher_approved", "teacher_approved_by_school", "teacher_revoked"])
        changes = {f: [before[f], getattr(user, f)] for f in before if before[f] != getattr(user, f)}
        if changes:
            audit.record(self.request, "update_user", user, **{k: [str(v) for v in pair] for k, pair in changes.items()})


class ReviewDecisionSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["lesson", "quiz", "resource"])
    id = serializers.IntegerField(min_value=1)
    # A real true/false: the text "false" must not approve anything.
    approve = serializers.BooleanField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class ReviewViewSet(viewsets.ViewSet):
    """Content awaiting approval before it appears in the public library."""

    permission_classes = [IsPlatformAdmin, RecentAuthentication]
    MODELS = {"lesson": Lesson, "quiz": Quiz, "resource": Resource}

    def list(self, request):
        lang = request_language(request)
        lessons = Lesson.objects.filter(status=ContentStatus.REVIEW).select_related("unit__subject", "author")
        quizzes = Quiz.objects.filter(status=ContentStatus.REVIEW).select_related("subject", "author")
        resources = Resource.objects.filter(status=ContentStatus.REVIEW).select_related("subject", "uploaded_by")
        return Response(
            [
                *[
                    {
                        "type": "lesson",
                        "id": les.id,
                        "title": les.title,
                        "slug": les.slug,
                        "subject": les.unit.subject.localized_name(lang),
                        "grade": les.unit.grade,
                        "author": les.author.display_name if les.author else None,
                        "updated_at": les.updated_at,
                    }
                    for les in lessons
                ],
                *[
                    {
                        "type": "quiz",
                        "id": q.id,
                        "title": q.title,
                        "subject": q.subject.localized_name(lang),
                        "grade": q.grade,
                        "author": q.author.display_name if q.author else None,
                        "updated_at": q.updated_at,
                    }
                    for q in quizzes
                ],
                *[
                    {
                        "type": "resource",
                        "id": r.id,
                        "title": r.title,
                        "subject": r.subject.localized_name(lang),
                        "grade": r.grade,
                        "author": r.uploaded_by.display_name if r.uploaded_by else None,
                        "updated_at": r.created_at,
                        "url": r.url,
                    }
                    for r in resources
                ],
            ]
        )

    @action(detail=False, methods=["post"])
    def decide(self, request):
        data = ReviewDecisionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        with transaction.atomic():
            obj = get_object_or_404(self.MODELS[v["type"]].objects.select_for_update(), pk=v["id"])
            approve = v["approve"]
            obj.status = ContentStatus.PUBLISHED if approve else ContentStatus.DRAFT
            obj.save(update_fields=["status"])
            audit.record(request, "approve_content" if approve else "reject_content", obj, note=v["note"])
        return Response({"status": obj.status})


@api_view(["GET"])
@permission_classes([IsPlatformAdmin, RecentAuthentication])
def admin_stats(request):
    week_ago = timezone.now() - timedelta(days=7)
    users_by_role = dict(User.objects.values_list("role").annotate(n=Count("id")))
    active_week = User.objects.filter(last_active_date__gte=timezone.localdate() - timedelta(days=7)).count()
    popular_lessons = (
        LessonProgress.objects.filter(completed_at__gte=week_ago)
        .values("lesson__title")
        .annotate(n=Count("id"))
        .order_by("-n")[:5]
    )
    popular_sims = (
        SimulationView.objects.filter(viewed_at__gte=week_ago)
        .values("simulation__title")
        .annotate(n=Count("id"))
        .order_by("-n")[:5]
    )
    students_by_grade = dict(User.objects.filter(role=User.Role.STUDENT).values_list("grade").annotate(n=Count("id")))
    return Response(
        {
            "users_by_role": users_by_role,
            "students_by_grade": students_by_grade,
            "active_last_7_days": active_week,
            "pending_teachers": User.objects.filter(role=User.Role.TEACHER, teacher_approved=False).count(),
            "subscriptions": revenue_summary(),
            "content": {
                "subjects": Subject.objects.count(),
                "lessons_published": Lesson.objects.filter(status=ContentStatus.PUBLISHED).count(),
                "questions": Question.objects.count(),
                "quizzes": Quiz.objects.filter(status=ContentStatus.PUBLISHED).count(),
                "simulations": Simulation.objects.count(),
                "awaiting_review": Lesson.objects.filter(status=ContentStatus.REVIEW).count()
                + Quiz.objects.filter(status=ContentStatus.REVIEW).count()
                + Resource.objects.filter(status=ContentStatus.REVIEW).count(),
            },
            "activity_last_7_days": {
                "attempts": Attempt.objects.filter(started_at__gte=week_ago).count(),
                "lessons_completed": LessonProgress.objects.filter(completed_at__gte=week_ago).count(),
                "simulation_views": SimulationView.objects.filter(viewed_at__gte=week_ago).count(),
            },
            "popular_lessons": [{"title": r["lesson__title"], "count": r["n"]} for r in popular_lessons],
            "popular_simulations": [{"title": r["simulation__title"], "count": r["n"]} for r in popular_sims],
            # The Django admin's secret address (None when it is off), for the Admin page's link.
            "django_admin_url": f"/{admin_prefix}" if (admin_prefix := admin_login.admin_url_prefix()) else None,
        }
    )


@api_view(["GET"])
@permission_classes([IsPlatformAdmin, RecentAuthentication])
def admin_audit(request):
    entries = AuditLog.objects.select_related("actor")
    if request.query_params.get("action"):
        entries = entries.filter(action=request.query_params["action"])
    return Response(
        [
            {
                "id": e.id,
                "created_at": e.created_at,
                "actor": e.actor.username if e.actor else None,
                "action": e.action,
                "target": f"{e.target_type}#{e.target_id}",
                "details": e.details,
            }
            for e in entries[:200]
        ]
    )
