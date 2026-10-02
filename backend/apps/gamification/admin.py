from django.contrib import admin

from .models import Badge, UserBadge, XPEvent


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("icon", "name", "code", "description")


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "awarded_at")
    list_filter = ("badge",)


@admin.register(XPEvent)
class XPEventAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "reason", "reference", "created_at")
    list_filter = ("reason",)
    search_fields = ("user__username",)
