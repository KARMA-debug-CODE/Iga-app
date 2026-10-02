from django.conf import settings
from django.db import models

from apps.classroom.models import generate_join_code
from apps.core.constants import GRADES


class StudyGroup(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    subject = models.ForeignKey(
        "curriculum.Subject", null=True, blank=True, on_delete=models.SET_NULL, related_name="study_groups"
    )
    grade = models.CharField(max_length=2, choices=GRADES, blank=True)
    is_private = models.BooleanField(default=False, help_text="Private groups can only be joined with the code")
    join_code = models.CharField(max_length=8, unique=True, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through="GroupMembership", related_name="study_groups")
    max_members = models.PositiveSmallIntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.join_code:
            code = generate_join_code()
            while StudyGroup.objects.filter(join_code=code).exists():
                code = generate_join_code()
            self.join_code = code
        super().save(*args, **kwargs)


class GroupMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MEMBER = "member", "Member"

    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_memberships")
    role = models.CharField(max_length=8, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "user"], name="unique_group_member")]


class Message(models.Model):
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    body = models.TextField(max_length=2000)
    is_hidden = models.BooleanField(default=False)
    hidden_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["id"]


class SharedNote(models.Model):
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    title = models.CharField(max_length=200)
    body = models.TextField(help_text="Markdown")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class MessageReport(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=300)
    resolved = models.BooleanField(default=False, db_index=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["message", "reporter"], name="unique_report_per_user")]
