from django.contrib import admin

from .models import LessonBookmark, LessonNote


@admin.register(LessonBookmark)
class LessonBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "created_at")
    search_fields = ("user__username", "lesson__title")
    raw_id_fields = ("user", "lesson")


@admin.register(LessonNote)
class LessonNoteAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "updated_at")
    search_fields = ("user__username", "lesson__title")
    raw_id_fields = ("user", "lesson")
    readonly_fields = ("created_at", "updated_at")
