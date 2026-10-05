from django.utils.translation import gettext_lazy
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsTeacher(BasePermission):
    message = gettext_lazy("Only approved teachers can do this.")

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.can_teach)


class IsPlatformAdmin(BasePermission):
    message = gettext_lazy("Only administrators can do this.")

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_platform_admin)


class IsTeacherOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return IsTeacher().has_permission(request, view)
