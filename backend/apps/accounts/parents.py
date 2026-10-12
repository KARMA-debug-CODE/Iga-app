"""Parent/guardian access: a student shares a code, the parent sees that child's progress (read-only)."""

import secrets
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assessments.models import Attempt
from apps.classroom.models import Assignment
from apps.classroom.views import assignment_status
from apps.core import audit
from apps.core.constants import ContentStatus
from apps.core.throttles import JoinRateThrottle
from apps.core.utils import request_language
from apps.curriculum.models import Lesson, LessonProgress, Subject

from .models import ParentInvite, ParentLink

INVITE_DAYS = 7
# No 0/O or 1/I: easy to read over the phone.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_code():
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(8))
        if not ParentInvite.objects.filter(code=code).exists():
            return code


class IsStudent(BasePermission):
    message = gettext_lazy("Only students can do this.")

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_student


class IsParent(BasePermission):
    message = gettext_lazy("Only parent or guardian accounts can do this.")

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_parent


def level_info(xp):
    from apps.core.views import level_from_xp

    return level_from_xp(xp)


def child_summary(student):
    week_ago = timezone.now() - timedelta(days=7)
    last = (
        Attempt.objects.filter(user=student)
        .exclude(status=Attempt.Status.IN_PROGRESS)
        .select_related("quiz")
        .order_by("-submitted_at")
        .first()
    )
    return {
        "id": student.id,
        "name": student.display_name,
        "first_name": student.first_name or student.username,
        "grade": student.grade,
        "school": student.school.name if student.school_id else "",
        "xp": student.xp,
        "level": level_info(student.xp)["level"],
        "streak_days": student.current_streak,
        "last_active": student.last_active_date,
        "lessons_this_week": LessonProgress.objects.filter(user=student, completed_at__gte=week_ago).count(),
        "latest_result": {"quiz": last.quiz.title, "percentage": last.percentage, "submitted_at": last.submitted_at}
        if last
        else None,
    }


def child_report(student, lang="en"):
    summary = child_summary(student)
    grade = student.grade
    subjects = []
    if grade:
        published = Q(units__lessons__status=ContentStatus.PUBLISHED, units__grade=grade)
        offered = (
            Subject.objects.filter(offered_o_level=True)
            if grade in ("S1", "S2", "S3")
            else Subject.objects.filter(offered_a_level=True)
        )
        done_ids = set(LessonProgress.objects.filter(user=student).values_list("lesson_id", flat=True))
        lessons_by_subject = {}
        for lesson_id, code in Lesson.objects.filter(status=ContentStatus.PUBLISHED, unit__grade=grade).values_list(
            "id", "unit__subject__code"
        ):
            lessons_by_subject.setdefault(code, []).append(lesson_id)
        for subject in offered.annotate(n=Count("units__lessons", filter=published, distinct=True)).order_by("order"):
            ids = lessons_by_subject.get(subject.code, [])
            subjects.append(
                {
                    "code": subject.code,
                    "name": subject.localized_name(lang),
                    "icon": subject.icon,
                    "lessons": subject.n,
                    "completed": sum(1 for i in ids if i in done_ids),
                }
            )
    attempts = (
        Attempt.objects.filter(user=student)
        .exclude(status=Attempt.Status.IN_PROGRESS)
        .select_related("quiz", "quiz__subject")
        .order_by("-submitted_at")[:10]
    )
    assignments = (
        Assignment.objects.filter(
            classroom__enrollments__student=student, classroom__enrollments__active=True, classroom__archived=False
        )
        .select_related("classroom")
        .order_by("-created_at")[:15]
    )
    return {
        **summary,
        "badges": [{"name": ub.badge.name, "icon": ub.badge.icon} for ub in student.badges.select_related("badge")],
        "subjects": subjects,
        "recent_results": [
            {
                "quiz": a.quiz.title,
                "subject": a.quiz.subject.localized_name(lang),
                "icon": a.quiz.subject.icon,
                "percentage": a.percentage,
                "status": a.status,
                "submitted_at": a.submitted_at,
            }
            for a in attempts
        ],
        "assignments": [
            {
                "title": a.title,
                "classroom": a.classroom.name,
                "due_at": a.due_at,
                "status": assignment_status(a, student),
            }
            for a in assignments
        ],
    }


class ParentCodeView(APIView):
    """Student: create a fresh code to give to a parent (replaces any unused code)."""

    permission_classes = [IsStudent]

    @transaction.atomic
    def post(self, request):
        ParentInvite.objects.filter(student=request.user, used_by__isnull=True).delete()
        invite = ParentInvite.objects.create(
            student=request.user, code=new_code(), expires_at=timezone.now() + timedelta(days=INVITE_DAYS)
        )
        return Response({"code": invite.code, "expires_at": invite.expires_at}, status=status.HTTP_201_CREATED)


class MyParentsView(APIView):
    """Student: see and remove the parents who can follow your progress."""

    permission_classes = [IsStudent]

    def get(self, request):
        links = ParentLink.objects.filter(student=request.user).select_related("parent")
        return Response(
            [{"id": link.parent_id, "name": link.parent.display_name, "linked_at": link.created_at} for link in links]
        )

    def delete(self, request, parent_id):
        deleted, _created = ParentLink.objects.filter(student=request.user, parent_id=parent_id).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        audit.record(request, "remove_parent_link", request.user, parent=parent_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChildrenView(APIView):
    permission_classes = [IsParent]

    def get_throttles(self):
        if self.request.method == "POST":
            return [JoinRateThrottle()]  # slows down guessing of link codes
        return super().get_throttles()

    def get(self, request):
        links = ParentLink.objects.filter(parent=request.user).select_related("student")
        return Response([child_summary(link.student) for link in links])

    @transaction.atomic
    def post(self, request):
        code = str(request.data.get("code", "")).strip().upper().replace(" ", "")
        invite = ParentInvite.objects.select_for_update().filter(code=code).select_related("student").first()
        # One answer for every unusable code (unknown, used, expired, or a deactivated account), so it
        # can't tell anyone which codes or accounts exist.
        if invite is None or invite.used_by_id or invite.expires_at < timezone.now() or not invite.student.is_active:
            raise ValidationError({"code": _("That code is not valid or has expired. Ask your child to make a new one.")})
        ParentLink.objects.get_or_create(parent=request.user, student=invite.student)
        invite.used_by = request.user
        invite.save(update_fields=["used_by"])
        audit.record(request, "link_parent", invite.student, parent=request.user.id)
        return Response(child_summary(invite.student), status=status.HTTP_201_CREATED)


class ChildDetailView(APIView):
    permission_classes = [IsParent]

    def _student(self, request, student_id):
        link = get_object_or_404(ParentLink.objects.select_related("student"), parent=request.user, student_id=student_id)
        return link.student

    def get(self, request, student_id):
        return Response(child_report(self._student(request, student_id), request_language(request)))

    def delete(self, request, student_id):
        student = self._student(request, student_id)
        ParentLink.objects.filter(parent=request.user, student=student).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotParent(BasePermission):
    """Keeps parent accounts out of student spaces such as study-group chats."""

    message = gettext_lazy("Study groups are for students and teachers.")

    def has_permission(self, request, view):
        return request.user.is_authenticated and not request.user.is_parent


def deny_parents(user):
    if user.is_parent:
        raise PermissionDenied(_("This is only for students and teachers."))
