from django.contrib import admin

from .models import GroupMembership, Message, MessageReport, SharedNote, StudyGroup


class MembershipInline(admin.TabularInline):
    model = GroupMembership
    raw_id_fields = ("user",)
    extra = 0


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "grade", "subject", "is_private", "created_at")
    list_filter = ("grade", "is_private")
    search_fields = ("name",)
    inlines = [MembershipInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("group", "author", "body", "is_hidden", "created_at")
    list_filter = ("is_hidden",)
    search_fields = ("body",)


@admin.register(MessageReport)
class MessageReportAdmin(admin.ModelAdmin):
    list_display = ("message", "reporter", "reason", "resolved", "created_at")
    list_filter = ("resolved",)


admin.site.register(SharedNote)
