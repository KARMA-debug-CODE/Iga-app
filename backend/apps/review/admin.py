from django.contrib import admin

from .models import ReviewItem


@admin.register(ReviewItem)
class ReviewItemAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "box", "due_on", "times_seen", "times_correct", "retired_at")
    list_filter = ("box", "retired_at")
    search_fields = ("user__username", "question__prompt")
    raw_id_fields = ("user", "question")
    readonly_fields = ("added_at", "last_reviewed_at")
