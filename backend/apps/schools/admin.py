from django.contrib import admin
from django.utils import timezone

from .models import BillingReminder, LedgerEntry, Payment, School, WebhookEvent


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "status", "paid_until", "created_at")
    list_filter = ("status", "district")
    search_fields = ("name", "district", "sector")
    # The paid-through date only moves with a payment or a ledger correction (Admin -> Schools in
    # the app), so every change to it is in the money ledger.
    readonly_fields = ("join_code", "paid_until", "created_by", "created_at", "verified_by", "verified_at")
    actions = ["verify"]

    @admin.action(description="Verify selected schools")
    def verify(self, request, queryset):
        queryset.update(status=School.Status.VERIFIED, verified_by=request.user, verified_at=timezone.now())


class ReadOnlyAdmin(admin.ModelAdmin):
    """Financial records: viewable, never added, changed or deleted here."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = (
        "reference",
        "school",
        "provider",
        "months",
        "amount",
        "currency",
        "status",
        "gross_amount",
        "provider_fee",
        "net_amount",
        "created_at",
        "paid_at",
    )
    list_filter = ("status", "provider", "currency")
    search_fields = ("reference", "provider_transaction_id", "external_reference", "school__name")


@admin.register(LedgerEntry)
class LedgerEntryAdmin(ReadOnlyAdmin):
    list_display = (
        "sequence",
        "created_at",
        "kind",
        "school",
        "currency",
        "gross_amount",
        "provider_fee",
        "net_amount",
        "months",
        "actor_name",
    )
    list_filter = ("kind", "currency")
    search_fields = ("reference", "note", "school__name", "entry_hash")


@admin.register(WebhookEvent)
class WebhookEventAdmin(ReadOnlyAdmin):
    list_display = ("received_at", "provider", "outcome", "reference", "transaction_id", "deliveries", "ip_address")
    list_filter = ("provider", "outcome", "signature_valid")
    search_fields = ("reference", "transaction_id", "digest")


@admin.register(BillingReminder)
class BillingReminderAdmin(admin.ModelAdmin):
    list_display = ("school", "kind", "paid_until", "sent_at")
