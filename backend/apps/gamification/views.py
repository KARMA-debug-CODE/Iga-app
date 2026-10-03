from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.classroom.models import Classroom

from .models import Badge, XPEvent

User = get_user_model()


def short_name(user):
    """First name + initial keeps leaderboards friendly without exposing full names of minors."""
    if user.first_name:
        initial = f" {user.last_name[0]}." if user.last_name else ""
        return f"{user.first_name}{initial}"
    return user.username


@api_view(["GET"])
def leaderboard(request):
    """?scope=grade|class|school&classroom=<id>&period=week|all"""
    user = request.user
    scope = request.query_params.get("scope", "grade")
    period = request.query_params.get("period", "week")
    if user.is_parent:
        return Response({"scope": scope, "period": period, "entries": [], "me": None})

    students = User.objects.filter(role=User.Role.STUDENT, is_active=True)
    if scope == "class":
        classroom = Classroom.objects.filter(pk=request.query_params.get("classroom")).first()
        allowed = classroom and (
            classroom.teacher_id == user.id or classroom.enrollments.filter(student=user).exists() or user.is_platform_admin
        )
        if not allowed:
            return Response({"detail": "Class not found."}, status=404)
        students = students.filter(enrollments__classroom=classroom)
    elif scope == "school":
        if not user.school:
            return Response({"scope": scope, "period": period, "entries": [], "me": None})
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
            .order_by("-points")
        )
        ranked = [(row["user"], row["points"]) for row in totals]
    else:
        ranked = list(students.order_by("-xp").values_list("id", "xp")[:500])
        ranked = [(uid, xp) for uid, xp in ranked if xp > 0]

    users = User.objects.in_bulk([uid for uid, _ in ranked])
    entries = []
    me = None
    for position, (uid, points) in enumerate(ranked, start=1):
        entry = {
            "rank": position,
            "user_id": uid,
            "name": short_name(users[uid]),
            "grade": users[uid].grade,
            "points": points,
            "is_me": uid == user.id,
        }
        if position <= 50:
            entries.append(entry)
        if uid == user.id:
            me = entry
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
