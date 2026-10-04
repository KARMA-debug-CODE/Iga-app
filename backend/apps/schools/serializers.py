from django.conf import settings
from rest_framework import serializers

from apps.accounts.models import User

from .constants import PROVINCE_OF
from .models import Payment, School


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


class SchoolAdminSerializer(serializers.ModelSerializer):
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
        from . import providers

        provider = providers.online_provider()
        return {
            "prices": {currency: str(amount) for currency, amount in settings.SUBSCRIPTION_PRICES.items()},
            "month_options": settings.SUBSCRIPTION_MONTH_OPTIONS,
            "online": provider is not None,
            "provider": provider.key if provider else "",
            "grace_days": settings.SUBSCRIPTION_GRACE_DAYS,
        }


class MemberSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

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
            "date_joined",
            "last_login",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="school.name", read_only=True)
    paid_by = serializers.CharField(source="created_by.display_name", read_only=True, default=None)

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


class PlatformSchoolSerializer(SchoolAdminSerializer):
    """Platform administrators see and edit everything about a school."""

    admins = serializers.SerializerMethodField()

    class Meta(SchoolAdminSerializer.Meta):
        fields = SchoolAdminSerializer.Meta.fields + ["admins", "verified_at"]
        read_only_fields = ["id", "status", "join_code", "created_at", "verified_at"]

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
    note = serializers.CharField(max_length=300)
