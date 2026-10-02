from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.constants import GRADES, LANGUAGES


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
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

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def can_teach(self):
        return (self.is_teacher and self.teacher_approved) or self.is_platform_admin

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        # Store empty emails as NULL so the unique constraint allows many blanks.
        if not self.email:
            self.email = None
        super().save(*args, **kwargs)
