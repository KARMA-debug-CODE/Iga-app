from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from apps.core.constants import GRADES, LANGUAGES


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        PARENT = "parent", "Parent or guardian"
        ADMIN = "admin", "Administrator"

    email = models.EmailField(unique=True, null=True, blank=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STUDENT, db_index=True)
    grade = models.CharField(max_length=2, choices=GRADES, blank=True)
    school = models.CharField(max_length=200, blank=True)
    preferred_language = models.CharField(max_length=2, choices=LANGUAGES, default="en")

    # Self-registered teachers must be approved by an administrator before they
    # can create classes or author content (safeguarding: classes contain minors).
    teacher_approved = models.BooleanField(default=False)

    # Gamification counters, denormalised from the XP ledger for fast reads.
    xp = models.PositiveIntegerField(default=0)
    streak_days = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)

    # Optional TOTP two-factor authentication (RFC 6238, works with any authenticator app).
    totp_secret = models.CharField(max_length=64, blank=True)
    totp_enabled = models.BooleanField(default=False)
    # Last 30-second time step accepted, so a code can't be used twice.
    totp_last_step = models.BigIntegerField(null=True, blank=True)

    class Meta(AbstractUser.Meta):
        constraints = [
            # "Aline" and "aline" (or two spellings of one email) must not be two accounts.
            models.UniqueConstraint(Lower("username"), name="unique_username_ci"),
            models.UniqueConstraint(Lower("email"), name="unique_email_ci"),
        ]

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_parent(self):
        return self.role == self.Role.PARENT

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def can_teach(self):
        return (self.is_teacher and self.teacher_approved) or self.is_platform_admin

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def short_name(self):
        """First name + initial: what other students see, so minors' full names aren't shown to strangers."""
        if self.first_name:
            initial = f" {self.last_name[0]}." if self.last_name else ""
            return f"{self.first_name}{initial}"
        return self.username

    @property
    def public_role(self):
        """The role shown to others. A teacher badge only appears once the account is approved."""
        if self.is_platform_admin:
            return "admin"
        if self.can_teach:
            return "teacher"
        return "student" if self.role == self.Role.TEACHER else self.role

    def save(self, *args, **kwargs):
        # Store empty emails as NULL so the unique constraint allows many blanks.
        if not self.email:
            self.email = None
        super().save(*args, **kwargs)


class ParentInvite(models.Model):
    """A short-lived code a student gives to a parent or guardian so they can follow their progress."""

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="parent_invites")
    code = models.CharField(max_length=12, unique=True)
    expires_at = models.DateTimeField()
    used_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} → {self.code}"


class ParentLink(models.Model):
    """Read-only access for a parent/guardian to one student's progress. Either side can remove it."""

    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="children_links")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="parent_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["parent", "student"], name="unique_parent_link")]

    def __str__(self):
        return f"{self.parent} → {self.student}"
