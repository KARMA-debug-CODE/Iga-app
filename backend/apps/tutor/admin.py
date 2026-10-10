from django.contrib import admin

from .models import TutorExchange


@admin.register(TutorExchange)
class TutorExchangeAdmin(admin.ModelAdmin):
    """Read-only log of questions to Santa and its answers, for safeguarding review."""

    list_display = ("created_at", "user", "subject", "lesson", "question", "stop_reason", "input_tokens", "output_tokens")
    list_filter = ("stop_reason", "model")
    search_fields = ("user__username", "message", "reply")
    readonly_fields = [f.name for f in TutorExchange._meta.fields]

    def has_add_permission(self, request):
        return False
