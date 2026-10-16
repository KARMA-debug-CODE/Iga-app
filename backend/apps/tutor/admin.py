from django.contrib import admin

from .models import SantaUsage, TutorExchange


@admin.register(TutorExchange)
class TutorExchangeAdmin(admin.ModelAdmin):
    """Read-only log of questions to Santa and its answers, for safeguarding review."""

    list_display = (
        "created_at",
        "user",
        "subject",
        "lesson",
        "question",
        "stop_reason",
        "flags",
        "input_tokens",
        "output_tokens",
    )
    list_filter = ("stop_reason", "model", "flags")
    search_fields = ("user__username", "message", "reply")
    readonly_fields = [f.name for f in TutorExchange._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(SantaUsage)
class SantaUsageAdmin(admin.ModelAdmin):
    """Santa's model use per student and day (what the allowances count). Read-only."""

    list_display = ("day", "user", "school", "questions", "input_tokens", "output_tokens", "limited")
    list_filter = ("day",)
    search_fields = ("user__username", "school__name")
    date_hierarchy = "day"
    readonly_fields = [f.name for f in SantaUsage._meta.fields]

    def has_add_permission(self, request):
        return False
