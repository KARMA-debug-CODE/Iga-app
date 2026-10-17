from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.accounts.models import User
from apps.core.serializers import SaveChangedFieldsMixin
from apps.core.text import CleanCharField

from .constants import PROVINCE_OF
from .models import LedgerEntry, Payment, School


class SchoolListSerializer(serializers.ModelSerializer):
    """What anyone may see when choosing a school."""

    province = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ["id", "name", "district", "province"]

    def get_province(self, school):
        return PROVINCE_OF.get(school.district, "")


def subscription_info(school):
    return {
        "state": school.subscription_state(),
        "active": school.subscription_active(),
        "paid_until": school.paid_until,
        "grace_ends": school.grace_ends(),
    }


class SchoolAdminSerializer(SaveChangedFieldsMixin, serializers.ModelSerializer):
    """The school administrator's view of their own school."""

    province = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()
    pricing = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = [
            "id",
            "name",
            "district",
            "province",
            "sector",
            "phone",
            "email",
            "status",
            "join_code",
            "subscription",
            "counts",
            "pricing",
            "created_at",
        ]
        read_only_fields = ["id", "name", "district", "status", "join_code", "created_at"]

    def get_province(self, school):
        return PROVINCE_OF.get(school.district, "")

    def get_subscription(self, school):
        return subscription_info(school)

    def get_counts(self, school):
        members = school.members.all()
        approved = members.filter(school_status=User.SchoolStatus.APPROVED)
        return {
            "students": approved.filter(role=User.Role.STUDENT).count(),
            "teachers": approved.filter(role=User.Role.TEACHER).count(),
            "admins": approved.filter(role=User.Role.SCHOOL_ADMIN).count(),
            "pending": members.filter(school_status=User.SchoolStatus.PENDING).count(),
        }

    def get_pricing(self, school):
        from . import billing, providers

        provider = providers.online_provider()
        return {**billing.price_list(), "online": provider is not None, "provider": provider.key if provider else ""}


class MemberSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    # An approved member who is a teacher the school can still confirm (see membership.decide).
    needs_teacher_confirmation = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "display_name",
            "role",
            "grade",
            "school_status",
            "school_approved_at",
            "teacher_approved",
            "needs_teacher_confirmation",
            "date_joined",
            "last_login",
        ]

    def get_needs_teacher_confirmation(self, user):
        from .membership import needs_teacher_confirmation

        return user.school_status == User.SchoolStatus.APPROVED and needs_teacher_confirmation(user)


class PaymentSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="school.name", read_only=True)
    paid_by = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "reference",
            "school",
            "school_name",
            "provider",
            "months",
            "amount",
            "currency",
            "status",
            "period_start",
            "period_end",
            "note",
            "paid_by",
            "created_at",
            "paid_at",
        ]

    def get_paid_by(self, payment):
        # A manual payment is recorded by the Iga team, so its creator is not the payer.
        if payment.provider == Payment.Provider.MANUAL or payment.created_by is None:
            return None
        return payment.created_by.display_name


class PlatformPaymentSerializer(PaymentSerializer):
    """For the Iga team only: what the payer was charged, the provider's fee and what reached Iga."""

    class Meta(PaymentSerializer.Meta):
        fields = PaymentSerializer.Meta.fields + [
            "gross_amount",
            "provider_fee",
            "net_amount",
            "external_reference",
            "provider_transaction_id",
        ]


class LedgerEntrySerializer(serializers.ModelSerializer):
    payment_reference = serializers.CharField(source="payment.reference", read_only=True, default="")
    corrects = serializers.IntegerField(source="corrects.sequence", read_only=True, default=None)

    class Meta:
        model = LedgerEntry
        fields = [
            "sequence",
            "kind",
            "school",
            "currency",
            "gross_amount",
            "provider_fee",
            "net_amount",
            "months",
            "paid_until_before",
            "paid_until_after",
            "payment_reference",
            "reference",
            "corrects",
            "actor_name",
            "note",
            "created_at",
            "entry_hash",
        ]
        read_only_fields = fields


class PlatformSchoolSerializer(SchoolAdminSerializer):
    """Platform administrators see and edit everything about a school."""

    admins = serializers.SerializerMethodField()

    class Meta(SchoolAdminSerializer.Meta):
        fields = SchoolAdminSerializer.Meta.fields + ["admins", "verified_at"]
        read_only_fields = ["id", "status", "join_code", "created_at", "verified_at"]

    def validate(self, attrs):
        name = attrs.get("name", getattr(self.instance, "name", ""))
        district = attrs.get("district", getattr(self.instance, "district", ""))
        clash = School.objects.filter(name__iexact=name, district=district)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({"name": _("Another school in this district already has this name.")})
        return attrs

    def get_admins(self, school):
        admins = school.members.filter(role=User.Role.SCHOOL_ADMIN).order_by("date_joined")
        return [
            {"id": u.id, "name": u.display_name, "username": u.username, "email": u.email, "status": u.school_status}
            for u in admins
        ]


class ChooseSchoolSerializer(serializers.Serializer):
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.filter(status=School.Status.VERIFIED), allow_null=True)
    school_code = serializers.CharField(required=False, allow_blank=True)


class DecideSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), max_length=500)
    approve = serializers.BooleanField()


class CheckoutSerializer(serializers.Serializer):
    months = serializers.IntegerField()
    currency = serializers.CharField(max_length=3)


class ManualPaymentSerializer(serializers.Serializer):
    months = serializers.IntegerField(min_value=1, max_value=24)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    currency = serializers.ChoiceField(choices=["USD", "RWF"])
    note = CleanCharField(max_length=300)
    # The bank transfer or receipt number: the same one can only be recorded once.
    external_reference = CleanCharField(max_length=100, required=False, allow_blank=True, default="")


class CorrectionSerializer(serializers.Serializer):
    """A refund (money paid back, a negative amount) or a correction of an earlier entry."""

    kind = serializers.ChoiceField(choices=[LedgerEntry.Kind.REFUND, LedgerEntry.Kind.CORRECTION])
    currency = serializers.ChoiceField(choices=["USD", "RWF"])
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    provider_fee = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, default=0)
    months = serializers.IntegerField(min_value=-24, max_value=24, required=False, default=0)
    corrects = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    note = CleanCharField(max_length=300)
