from django.contrib import admin

from .models import CodeRunUsage


@admin.register(CodeRunUsage)
class CodeRunUsageAdmin(admin.ModelAdmin):
    """Code runner use per user and day (what the daily limits count). Read-only."""

    list_display = ("day", "user", "runs", "cpu_ms", "limited")
    list_filter = ("day",)
    search_fields = ("user__username",)
    date_hierarchy = "day"
    readonly_fields = [f.name for f in CodeRunUsage._meta.fields]

    def has_add_permission(self, request):
        return False
