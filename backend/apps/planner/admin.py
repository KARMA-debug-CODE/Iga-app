from django.contrib import admin

from .models import ExamDate, StudyPlan


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "weekly_goal_lessons", "updated_at")
    search_fields = ("user__username",)
    raw_id_fields = ("user",)


@admin.register(ExamDate)
class ExamDateAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "date")
    search_fields = ("user__username", "title")
    raw_id_fields = ("user",)
