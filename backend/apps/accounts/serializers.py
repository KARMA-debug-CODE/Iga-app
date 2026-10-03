from django.contrib.auth import password_validation
from rest_framework import serializers

from apps.core.constants import GRADE_CODES

from .models import User


class UserSerializer(serializers.ModelSerializer):
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
            "preferred_language",
            "xp",
            "streak_days",
            "teacher_approved",
            "totp_enabled",
            "badges",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "username",
            "role",
            "teacher_approved",
            "xp",
            "streak_days",
            "totp_enabled",
            "badges",
            "date_joined",
        ]

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


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=[User.Role.STUDENT, User.Role.TEACHER, User.Role.PARENT], default=User.Role.STUDENT)

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
            "preferred_language",
        ]

    def validate(self, attrs):
        role = attrs.get("role", User.Role.STUDENT)
        if role == User.Role.STUDENT and not attrs.get("grade"):
            raise serializers.ValidationError({"grade": "Students must choose their grade (S1–S6)."})
        if role != User.Role.STUDENT:
            attrs["grade"] = ""
        candidate = User(**{k: v for k, v in attrs.items() if k != "password"})
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

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
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
        password_validation.validate_password(attrs["new_password"], user)
        return attrs


class OTPSerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=8)
