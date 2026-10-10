from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ParentInvite, ParentLink, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "teacher_approved", "grade", "school", "school_status", "xp", "is_active")
    list_filter = ("role", "teacher_approved", "school_status", "grade", "is_active")
    autocomplete_fields = ("school",)
    search_fields = ("username", "email", "first_name", "last_name", "school__name")
    actions = ["approve_teachers"]
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Learning profile",
            {
                "fields": (
                    "role",
                    "teacher_approved",
                    "teacher_approved_by_school",
                    "teacher_revoked",
                    "grade",
                    "combination",
                    "school",
                    "school_status",
                    "preferred_language",
                )
            },
        ),
        ("Progress", {"fields": ("xp", "streak_days", "last_active_date")}),
        ("Security", {"fields": ("totp_enabled",)}),
    )
    readonly_fields = ("totp_enabled", "teacher_approved_by_school")

    @admin.action(description="Approve selected teachers")
    def approve_teachers(self, request, queryset):
        queryset.filter(role=User.Role.TEACHER).update(
            teacher_approved=True, teacher_approved_by_school=None, teacher_revoked=False
        )

    def save_model(self, request, obj, form, change):
        if change and "teacher_approved" in form.changed_data:
            obj.set_teacher_approval(obj.teacher_approved)  # the Iga team's decision overrides a school's
        super().save_model(request, obj, form, change)


@admin.register(ParentLink)
class ParentLinkAdmin(admin.ModelAdmin):
    list_display = ("parent", "student", "created_at")
    search_fields = ("parent__username", "student__username")
    raw_id_fields = ("parent", "student")


@admin.register(ParentInvite)
class ParentInviteAdmin(admin.ModelAdmin):
    list_display = ("student", "code", "expires_at", "used_by")
    readonly_fields = ("code",)
