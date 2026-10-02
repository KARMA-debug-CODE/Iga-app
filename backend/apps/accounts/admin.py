from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "teacher_approved", "grade", "school", "xp", "is_active")
    list_filter = ("role", "teacher_approved", "grade", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "school")
    actions = ["approve_teachers"]
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Learning profile",
            {"fields": ("role", "teacher_approved", "grade", "school", "preferred_language")},
        ),
        ("Progress", {"fields": ("xp", "streak_days", "last_active_date")}),
        ("Security", {"fields": ("totp_enabled",)}),
    )
    readonly_fields = ("totp_enabled",)

    @admin.action(description="Approve selected teachers")
    def approve_teachers(self, request, queryset):
        queryset.filter(role=User.Role.TEACHER).update(teacher_approved=True)
