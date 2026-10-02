from django.contrib import admin

from .models import Assignment, Classroom, Enrollment


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    raw_id_fields = ("student",)
    extra = 0


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("name", "grade", "subject", "teacher", "join_code", "archived")
    list_filter = ("grade", "subject", "archived")
    search_fields = ("name", "teacher__username", "join_code")
    inlines = [EnrollmentInline]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "classroom", "due_at", "created_at")
    list_filter = ("classroom__grade",)
