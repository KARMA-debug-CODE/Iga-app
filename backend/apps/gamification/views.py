from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.classroom.models import Classroom

from .models import Badge, XPEvent

User = get_user_model()


TOP = 50


def short_name(user):
    return user.short_name


def _empty(scope, period):
    return Response({"scope": scope, "period": period, "entries": [], "me": None})


@api_view(["GET"])
def leaderboard(request):
    """?scope=grade|class|school&classroom=<id>&period=week|all

    Grade and school boards are for students (teachers use their class boards). Only the
    top 50 are listed; everyone else sees their own rank.
    """
    user = request.user
    scope = request.query_params.get("scope", "grade")
    period = request.query_params.get("period", "week")
    if user.is_parent:
        return _empty(scope, period)

    students = User.objects.filter(role=User.Role.STUDENT, is_active=True)
    if scope == "class":
        classroom = Classroom.objects.filter(pk=request.query_params.get("classroom") or None).first()
        allowed = classroom and (
            classroom.teacher_id == user.id or classroom.enrollments.filter(student=user).exists() or user.is_platform_admin
        )
        if not allowed:
            return Response({"detail": "Class not found."}, status=404)
        students = students.filter(enrollments__classroom=classroom)
    elif not (user.is_student or user.is_platform_admin):
        return _empty(scope, period)
    elif scope == "school":
        if not user.school:
            return _empty(scope, period)
        students = students.filter(school__iexact=user.school)
    else:
        grade = request.query_params.get("grade") or user.grade
        if grade:
            students = students.filter(grade=grade)

    if period == "week":
        since = timezone.now() - timedelta(days=7)
        totals = (
            XPEvent.objects.filter(user__in=students, created_at__gte=since)
            .values("user")
            .annotate(points=Sum("amount"))
            .filter(points__gt=0)
        )
        top = [(row["user"], row["points"]) for row in totals.order_by("-points", "user")[:TOP]]
        my_points = next(iter(totals.filter(user=user.pk).values_list("points", flat=True)), None)
        ahead_of_me = (lambda p: totals.filter(points__gt=p).count()) if my_points else None
    else:
        ranked = students.filter(xp__gt=0)
        top = list(ranked.order_by("-xp", "id").values_list("id", "xp")[:TOP])
        my_points = user.xp if user.xp > 0 and students.filter(pk=user.pk).exists() else None
        ahead_of_me = (lambda p: ranked.filter(xp__gt=p).count()) if my_points else None

    users = User.objects.in_bulk([uid for uid, _ in top])
    entries = []
    for uid, points in top:
        rank = 1 + sum(1 for _, p in top if p > points)  # ties share a rank
        entries.append(
            {"rank": rank, "name": users[uid].short_name, "grade": users[uid].grade, "points": points, "is_me": uid == user.pk}
        )
    me = next((e for e in entries if e["is_me"]), None)
    if me is None and my_points:
        me = {
            "rank": ahead_of_me(my_points) + 1,
            "name": user.short_name,
            "grade": user.grade,
            "points": my_points,
            "is_me": True,
        }
    return Response({"scope": scope, "period": period, "entries": entries, "me": me})


@api_view(["GET"])
def badges(request):
    earned = {ub.badge_id: ub.awarded_at for ub in request.user.badges.all()}
    return Response(
        [
            {
                "code": b.code,
                "name": b.name,
                "description": b.description,
                "icon": b.icon,
                "earned": b.id in earned,
                "awarded_at": earned.get(b.id),
            }
            for b in Badge.objects.order_by("id")
        ]
    )
