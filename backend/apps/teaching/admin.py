from django.contrib import admin

from .models import PackAssignment, TeachingPack


class PackAssignmentInline(admin.TabularInline):
    model = PackAssignment
    extra = 0
    can_delete = False
    readonly_fields = ("what", "quiz", "assignment", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TeachingPack)
class TeachingPackAdmin(admin.ModelAdmin):
    list_display = ("__str__", "created_by", "created_at", "ai_used")
    search_fields = ("created_by__username", "classroom__name")
    readonly_fields = ("classroom", "unit", "lesson", "created_by", "created_at", "language", "document", "plan_edits", "ai_used")
    inlines = [PackAssignmentInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
