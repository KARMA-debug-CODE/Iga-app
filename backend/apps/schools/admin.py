from django.contrib import admin
from django.utils import timezone

from .models import BillingReminder, Payment, School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "status", "paid_until", "created_at")
    list_filter = ("status", "district")
    search_fields = ("name", "district", "sector")
    readonly_fields = ("join_code", "created_by", "created_at", "verified_by", "verified_at")
    actions = ["verify"]

    @admin.action(description="Verify selected schools")
    def verify(self, request, queryset):
        queryset.update(status=School.Status.VERIFIED, verified_by=request.user, verified_at=timezone.now())


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "school", "provider", "months", "amount", "currency", "status", "created_at", "paid_at")
    list_filter = ("status", "provider", "currency")
    search_fields = ("reference", "provider_transaction_id", "school__name")
    # Payments change a school's access; record them through the app so they are applied and audited.
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(BillingReminder)
class BillingReminderAdmin(admin.ModelAdmin):
    list_display = ("school", "kind", "paid_until", "sent_at")
