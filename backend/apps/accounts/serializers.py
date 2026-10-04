from django.contrib.auth import password_validation
from django.db import transaction
from rest_framework import serializers

from apps.core.constants import GRADE_CODES
from apps.schools.access import content_access
from apps.schools.constants import DISTRICTS
from apps.schools.membership import choose_school
from apps.schools.models import School

from .models import User


def school_summary(user):
    school = user.school
    if school is None:
        return None
    data = {
        "id": school.id,
        "name": school.name,
        "district": school.district,
        "verified": school.is_verified,
        "suspended": school.status == school.Status.SUSPENDED,
    }
    if user.school_status == User.SchoolStatus.APPROVED:
        data["subscription"] = {"state": school.subscription_state(), "paid_until": school.paid_until}
    return data


class UserSerializer(serializers.ModelSerializer):
    streak_days = serializers.IntegerField(source="current_streak", read_only=True)
    school = serializers.SerializerMethodField()
    access = serializers.SerializerMethodField()
    display_name = serializers.CharField(read_only=True)
    badges = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "role",
            "grade",
            "school",
            "school_status",
            "access",
            "preferred_language",
            "xp",
            "streak_days",
            "teacher_approved",
            "totp_enabled",
            "must_change_password",
            "badges",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "username",
            "role",
            "school_status",
            "teacher_approved",
            "xp",
            "streak_days",
            "totp_enabled",
            "must_change_password",
            "badges",
            "date_joined",
        ]

    def get_school(self, user):
        return school_summary(user)

    def get_access(self, user):
        result = content_access(user)
        return {"premium": result.premium, "reason": result.reason}

    def get_badges(self, user):
        return [
            {"code": ub.badge.code, "name": ub.badge.name, "icon": ub.badge.icon, "awarded_at": ub.awarded_at}
            for ub in user.badges.select_related("badge").all()
        ]

    def validate_grade(self, value):
        if value and value not in GRADE_CODES:
            raise serializers.ValidationError("Unknown grade.")
        return value

    def validate_email(self, value):
        if not value:
            return None
        value = value.lower()
        others = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value


class PublicUserSerializer(serializers.ModelSerializer):
    """What other students may see about a user (no email, no school)."""

    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "display_name", "role", "grade", "xp"]


class NewSchoolSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    district = serializers.ChoiceField(choices=DISTRICTS)
    sector = serializers.CharField(max_length=80, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_name(self, value):
        return " ".join(value.split())


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=[User.Role.STUDENT, User.Role.TEACHER, User.Role.PARENT, User.Role.SCHOOL_ADMIN], default=User.Role.STUDENT
    )
    school = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.filter(status=School.Status.VERIFIED), required=False, allow_null=True
    )
    school_code = serializers.CharField(required=False, allow_blank=True, write_only=True)
    # School administrators registering a school that isn't on Iga yet.
    new_school = NewSchoolSerializer(required=False, write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "grade",
            "school",
            "school_code",
            "new_school",
            "preferred_language",
        ]

    def validate(self, attrs):
        role = attrs.get("role", User.Role.STUDENT)
        if role == User.Role.STUDENT and not attrs.get("grade"):
            raise serializers.ValidationError({"grade": "Students must choose their grade (S1–S6)."})
        if role != User.Role.STUDENT:
            attrs["grade"] = ""
        if role == User.Role.PARENT and (attrs.get("school") or attrs.get("new_school")):
            raise serializers.ValidationError({"school": "Parents don't join a school; link to your child instead."})
        if role == User.Role.SCHOOL_ADMIN:
            if not attrs.get("email"):
                raise serializers.ValidationError(
                    {"email": "School administrators need an email address for receipts and reminders."}
                )
            if bool(attrs.get("school")) == bool(attrs.get("new_school")):
                raise serializers.ValidationError({"school": "Choose your school, or register a new one (not both)."})
            if attrs.get("school_code"):
                raise serializers.ValidationError(
                    {"school_code": "School administrators are approved by the Iga team or an existing administrator."}
                )
        elif attrs.get("new_school"):
            raise serializers.ValidationError({"new_school": "Only school administrators register schools."})
        new_school = attrs.get("new_school")
        if new_school and School.objects.filter(name__iexact=new_school["name"], district=new_school["district"]).exists():
            raise serializers.ValidationError({"new_school": "That school is already on Iga. Choose it from the list instead."})
        candidate = User(**{k: v for k, v in attrs.items() if k not in ("password", "school", "school_code", "new_school")})
        password_validation.validate_password(attrs["password"], candidate)
        return attrs

    def validate_username(self, value):
        if "@" in value:
            raise serializers.ValidationError("Usernames can't contain @. Use letters, numbers, dots or dashes.")
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("That username is taken.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower() if value else value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        school = validated_data.pop("school", None)
        code = validated_data.pop("school_code", "")
        new_school = validated_data.pop("new_school", None)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if new_school:
            # Waits for the Iga team to verify the school (and this administrator).
            created = School.objects.create(created_by=user, **new_school)
            user.school = created
            user.school_status = User.SchoolStatus.PENDING
            user.save(update_fields=["school", "school_status"])
        elif school:
            choose_school(user, school, code)
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Username or email")
    password = serializers.CharField(write_only=True)
    otp = serializers.CharField(required=False, allow_blank=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "Incorrect password."})
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError({"new_password": "Choose a password different from the current one."})
        password_validation.validate_password(attrs["new_password"], user)
        return attrs


class OTPSerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=8)
