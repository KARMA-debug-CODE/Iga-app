from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "school", "language", "handled_at")
    list_filter = ("handled_at", "language")
    search_fields = ("name", "email", "school", "message")
    readonly_fields = ("name", "email", "school", "message", "language", "user", "created_at")
    fields = readonly_fields + ("handled_at", "handled_by")
    date_hierarchy = "created_at"
