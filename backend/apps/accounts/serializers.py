from django.contrib.auth import password_validation
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.core.constants import A_LEVEL_GRADES, GRADE_CODES
from apps.core.serializers import SaveChangedFieldsMixin
from apps.core.text import CleanCharField
from apps.schools.access import content_access
from apps.schools.constants import DISTRICTS
from apps.schools.membership import choose_school
from apps.schools.models import School

from . import avatar, legal
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


class UserSerializer(SaveChangedFieldsMixin, serializers.ModelSerializer):
    streak_days = serializers.IntegerField(source="current_streak", read_only=True)
    school = serializers.SerializerMethodField()
    access = serializers.SerializerMethodField()
    display_name = serializers.CharField(read_only=True)
    badges = serializers.SerializerMethodField()
    combination_subjects = serializers.ListField(child=serializers.CharField(), read_only=True)
    # True while the account hasn't accepted the current Terms of Use and Privacy Policy (legal.py).
    consent_required = serializers.SerializerMethodField()

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
            "combination",
            "combination_subjects",
            "school",
            "school_status",
            "access",
            "preferred_language",
            "avatar",
            "xp",
            "streak_days",
            "teacher_approved",
            "totp_enabled",
            "must_change_password",
            "badges",
            "date_joined",
            "consent_required",
            "terms_version",
            "terms_accepted_at",
            "deletion_due_at",
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
            "consent_required",
            "terms_version",
            "terms_accepted_at",
            "deletion_due_at",
        ]
        # Uniqueness is checked in validate_email, which counts "already used" answers (enumeration.py).
        extra_kwargs = {"email": {"validators": []}}

    email_in_use = False

    def validate_avatar(self, value):
        return avatar.clean(value)

    def get_school(self, user):
        return school_summary(user)

    def get_consent_required(self, user):
        return legal.consent_required(user)

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
            raise serializers.ValidationError(_("Unknown grade."))
        return value

    def validate(self, attrs):
        user = self.instance
        if attrs.get("combination") and user is not None and not user.is_student:
            raise serializers.ValidationError({"combination": _("Only students in S4–S6 choose a combination.")})
        # A combination belongs to A-level: moving to S1–S3 (or saving one there) leaves none.
        if user is not None and ("grade" in attrs or "combination" in attrs):
            if attrs.get("grade", user.grade) not in A_LEVEL_GRADES:
                attrs["combination"] = ""
        return attrs

    def validate_email(self, value):
        if not value:
            if self.instance is not None and self.instance.is_school_admin:
                raise serializers.ValidationError(_("School administrators need an email address for receipts and reminders."))
            return None
        value = value.lower()
        others = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            self.email_in_use = True
            raise serializers.ValidationError(_("An account with this email already exists."))
        return value


class PublicUserSerializer(serializers.ModelSerializer):
    """What other students may see about a user (no email, no school)."""

    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "display_name", "role", "grade", "xp", "avatar"]


class NewSchoolSerializer(serializers.Serializer):
    name = CleanCharField(max_length=200)
    district = serializers.ChoiceField(choices=DISTRICTS)
    sector = CleanCharField(max_length=80, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_name(self, value):
        return " ".join(value.split())


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, max_length=4096)
    role = serializers.ChoiceField(
        choices=[User.Role.STUDENT, User.Role.TEACHER, User.Role.PARENT, User.Role.SCHOOL_ADMIN], default=User.Role.STUDENT
    )
    school = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.filter(status=School.Status.VERIFIED), required=False, allow_null=True
    )
    school_code = serializers.CharField(required=False, allow_blank=True, write_only=True)
    # School administrators registering a school that isn't on Iga yet.
    new_school = NewSchoolSerializer(required=False, write_only=True)
    # The Terms of Use and Privacy Policy must be accepted (legal.py). terms_version is the version the form
    # showed: if the texts changed meanwhile, the person is asked to read them again.
    accept_terms = serializers.BooleanField(write_only=True)
    terms_version = serializers.CharField(write_only=True, required=False, max_length=32)

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
            "accept_terms",
            "terms_version",
        ]
        # Uniqueness is checked in validate_email, which counts "already used" answers (enumeration.py).
        extra_kwargs = {"email": {"validators": []}}

    email_in_use = False
    # What the form sends besides the account's own fields.
    NOT_USER_FIELDS = ("password", "school", "school_code", "new_school", "accept_terms", "terms_version")

    def validate_accept_terms(self, value):
        if value is not True:
            raise serializers.ValidationError(_("To create an account, accept the Terms of Use and the Privacy Policy."))
        return value

    def validate_terms_version(self, value):
        if value != legal.current_version():
            raise serializers.ValidationError(
                _("The Terms of Use and the Privacy Policy have just changed. Read them again, then accept them.")
            )
        return value

    def validate(self, attrs):
        role = attrs.get("role", User.Role.STUDENT)
        if role == User.Role.STUDENT and not attrs.get("grade"):
            raise serializers.ValidationError({"grade": _("Students must choose their grade (S1–S6).")})
        if role != User.Role.STUDENT:
            attrs["grade"] = ""
        if role == User.Role.PARENT and (attrs.get("school") or attrs.get("new_school")):
            raise serializers.ValidationError({"school": _("Parents don't join a school; link to your child instead.")})
        if role == User.Role.SCHOOL_ADMIN:
            if not attrs.get("email"):
                raise serializers.ValidationError(
                    {"email": _("School administrators need an email address for receipts and reminders.")}
                )
            if bool(attrs.get("school")) == bool(attrs.get("new_school")):
                raise serializers.ValidationError({"school": _("Choose your school, or register a new one (not both).")})
            if attrs.get("school_code"):
                raise serializers.ValidationError(
                    {"school_code": _("School administrators are approved by the Iga team or an existing administrator.")}
                )
        elif attrs.get("new_school"):
            raise serializers.ValidationError({"new_school": _("Only school administrators register schools.")})
        new_school = attrs.get("new_school")
        existing = (
            School.objects.filter(name__iexact=new_school["name"], district=new_school["district"]).first()
            if new_school
            else None
        )
        if existing is not None:
            if existing.is_verified:
                raise serializers.ValidationError(
                    {"new_school": _("That school is already on Iga. Choose it from the list instead.")}
                )
            raise serializers.ValidationError(
                {
                    "new_school": _(
                        "That school has already been registered and is waiting for the Iga team. "
                        "If you run it, contact the Iga team."
                    )
                }
            )
        candidate = User(**{k: v for k, v in attrs.items() if k not in self.NOT_USER_FIELDS})
        password_validation.validate_password(attrs["password"], candidate)
        return attrs

    def validate_username(self, value):
        if "@" in value:
            raise serializers.ValidationError(_("Usernames can't contain @. Use letters, numbers, dots or dashes."))
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(_("That username is taken."))
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            self.email_in_use = True
            raise serializers.ValidationError(
                _("This email address already has an account. If it's yours, log in or reset your password.")
            )
        return value.lower() if value else value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        school = validated_data.pop("school", None)
        code = validated_data.pop("school_code", "")
        new_school = validated_data.pop("new_school", None)
        validated_data.pop("accept_terms")
        validated_data.pop("terms_version", None)
        user = User(**validated_data)
        user.set_password(password)
        # Accepted on the form (validate_accept_terms): the current version, now. RegisterView adds the audit entry.
        user.terms_version = legal.current_version()
        user.terms_accepted_at = timezone.now()
        user.save()
        if new_school:
            # Waits for the Iga team to verify the school (and this administrator).
            try:
                with transaction.atomic():
                    created = School.objects.create(created_by=user, **new_school)
            except IntegrityError:  # registered by someone else a moment ago
                raise serializers.ValidationError(
                    {"new_school": _("That school has just been registered. Choose it from the list.")}
                )
            user.school = created
            user.school_status = User.SchoolStatus.PENDING
            user.save(update_fields=["school", "school_status"])
        elif school:
            choose_school(user, school, code)
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Username or email", max_length=254)
    password = serializers.CharField(write_only=True, max_length=4096)
    otp = serializers.CharField(required=False, allow_blank=True, max_length=16)


class ChangePasswordSerializer(serializers.Serializer):
    """The view has already checked current_password (with the re-authentication lockout)."""

    current_password = serializers.CharField(write_only=True, max_length=4096)
    new_password = serializers.CharField(write_only=True, min_length=8, max_length=4096)

    def validate(self, attrs):
        user = self.context["request"].user
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError({"new_password": _("Choose a password different from the current one.")})
        password_validation.validate_password(attrs["new_password"], user)
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Username or email", max_length=254)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)
    new_password = serializers.CharField(write_only=True, min_length=8, max_length=4096)


class OTPSerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=8)


class AcceptTermsSerializer(serializers.Serializer):
    """The version the app showed; accepting an older one (the texts changed meanwhile) is refused."""

    version = serializers.CharField(max_length=32)

    def validate_version(self, value):
        if value != legal.current_version():
            raise serializers.ValidationError(
                _("The Terms of Use and the Privacy Policy have just changed. Read them again, then accept them.")
            )
        return value


class DeleteAccountSerializer(serializers.Serializer):
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if value is not True:
            raise serializers.ValidationError(_("Tick the box to confirm that you want to delete your account."))
        return value
