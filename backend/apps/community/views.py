from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.serializers import PublicUserSerializer
from apps.core import audit
from apps.core.permissions import IsPlatformAdmin
from apps.gamification import services as gamification

from .models import GroupMembership, Message, MessageReport, SharedNote, StudyGroup

REMOVED_TEXT = "[message removed by a moderator]"


class StudyGroupSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    is_member = serializers.BooleanField(read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True, default=None)
    subject_icon = serializers.CharField(source="subject.icon", read_only=True, default="👥")
    join_code = serializers.SerializerMethodField()

    class Meta:
        model = StudyGroup
        fields = [
            "id",
            "name",
            "description",
            "subject",
            "subject_name",
            "subject_icon",
            "grade",
            "is_private",
            "max_members",
            "member_count",
            "is_member",
            "join_code",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_join_code(self, group):
        return group.join_code if getattr(group, "is_member", False) else None


class MessageSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "author", "body", "is_hidden", "created_at"]

    def get_author(self, message):
        if message.author is None:
            return None
        return {"id": message.author_id, "name": message.author.display_name, "role": message.author.role}

    def get_body(self, message):
        return REMOVED_TEXT if message.is_hidden else message.body


class SharedNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True, default=None)

    class Meta:
        model = SharedNote
        fields = ["id", "title", "body", "author_name", "created_at"]
        read_only_fields = ["id", "author_name", "created_at"]


def can_moderate(user, group):
    if user.is_platform_admin or user.can_teach:
        return True
    return GroupMembership.objects.filter(group=group, user=user, role=GroupMembership.Role.OWNER).exists()


class StudyGroupViewSet(viewsets.ModelViewSet):
    serializer_class = StudyGroupSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        membership = GroupMembership.objects.filter(group=OuterRef("pk"), user=user)
        qs = (
            StudyGroup.objects.select_related("subject")
            .annotate(member_count=Count("memberships", distinct=True), is_member=Exists(membership))
            .order_by("-created_at")
        )
        if not user.is_platform_admin:
            qs = qs.filter(Q(is_private=False) | Q(is_member=True))
        params = self.request.query_params
        if params.get("mine"):
            qs = qs.filter(is_member=True)
        if params.get("grade"):
            qs = qs.filter(grade=params["grade"])
        if params.get("subject"):
            qs = qs.filter(subject__code=params["subject"])
        return qs

    def _member_group(self, pk):
        group = get_object_or_404(self.get_queryset(), pk=pk)
        if not group.is_member and not self.request.user.is_platform_admin:
            raise PermissionDenied("Join the group first.")
        return group

    def perform_create(self, serializer):
        group = serializer.save(created_by=self.request.user)
        GroupMembership.objects.create(group=group, user=self.request.user, role=GroupMembership.Role.OWNER)
        gamification.on_group_joined(self.request.user, group)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        group = self.get_queryset().get(pk=serializer.instance.pk)
        return Response(self.get_serializer(group).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        if not can_moderate(self.request.user, serializer.instance):
            raise PermissionDenied("Only the group owner can edit the group.")
        serializer.save()

    def perform_destroy(self, instance):
        is_owner = GroupMembership.objects.filter(
            group=instance, user=self.request.user, role=GroupMembership.Role.OWNER
        ).exists()
        if not (is_owner or self.request.user.is_platform_admin):
            raise PermissionDenied("Only the group owner can delete the group.")
        audit.record(self.request, "delete_group", instance, name=instance.name)
        instance.delete()

    def retrieve(self, request, *args, **kwargs):
        group = self.get_object()
        data = self.get_serializer(group).data
        if group.is_member or request.user.is_platform_admin:
            members = GroupMembership.objects.filter(group=group).select_related("user")
            data["members"] = [{**PublicUserSerializer(m.user).data, "group_role": m.role} for m in members]
            data["can_moderate"] = can_moderate(request.user, group)
        return Response(data)

    def _join(self, request, group):
        if group.memberships.count() >= group.max_members:
            raise ValidationError("This group is full.")
        _, created = GroupMembership.objects.get_or_create(group=group, user=request.user)
        if created:
            gamification.on_group_joined(request.user, group)
        return Response(self.get_serializer(self.get_queryset().get(pk=group.pk)).data)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        group = self.get_object()
        if group.is_private:
            raise PermissionDenied("This group is private; ask a member for the code.")
        return self._join(request, group)

    @action(detail=False, methods=["post"], url_path="join-by-code")
    def join_by_code(self, request):
        code = (request.data.get("code") or "").strip().upper()
        group = StudyGroup.objects.filter(join_code=code).first()
        if not group:
            raise ValidationError({"code": "No group has that code."})
        return self._join(request, group)

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        group = self._member_group(pk)
        GroupMembership.objects.filter(group=group, user=request.user).delete()
        # Hand ownership to the longest-standing member so the group stays moderated.
        if not group.memberships.filter(role=GroupMembership.Role.OWNER).exists():
            successor = group.memberships.order_by("joined_at").first()
            if successor:
                successor.role = GroupMembership.Role.OWNER
                successor.save(update_fields=["role"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_throttles(self):
        # Rate-limit posting (not polling) chat messages.
        if self.action == "messages" and self.request.method == "POST":
            self.throttle_scope = "chat"
        return super().get_throttles()

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        group = self._member_group(pk)
        if request.method == "POST":
            return self._post_message(request, group)
        qs = group.messages.select_related("author")
        after = request.query_params.get("after")
        if after and after.isdigit():
            qs = qs.filter(id__gt=int(after))
            return Response(MessageSerializer(qs[:200], many=True).data)
        latest = list(qs.order_by("-id")[:50])[::-1]
        return Response(MessageSerializer(latest, many=True).data)

    def _post_message(self, request, group):
        body = (request.data.get("body") or "").strip()
        if not body:
            raise ValidationError({"body": "Write something first."})
        if len(body) > 2000:
            raise ValidationError({"body": "Messages are limited to 2000 characters."})
        message = Message.objects.create(group=group, author=request.user, body=body)
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def notes(self, request, pk=None):
        group = self._member_group(pk)
        if request.method == "POST":
            serializer = SharedNoteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(group=group, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(SharedNoteSerializer(group.notes.select_related("author"), many=True).data)


class MessageViewSet(viewsets.GenericViewSet):
    queryset = Message.objects.select_related("group")

    def get_object(self):
        message = get_object_or_404(self.queryset, pk=self.kwargs["pk"])
        user = self.request.user
        if not user.is_platform_admin and not GroupMembership.objects.filter(group=message.group, user=user).exists():
            raise PermissionDenied("You are not in this group.")
        return message

    @action(detail=True, methods=["post"])
    def report(self, request, pk=None):
        message = self.get_object()
        reason = (request.data.get("reason") or "").strip()[:300] or "No reason given"
        MessageReport.objects.get_or_create(message=message, reporter=request.user, defaults={"reason": reason})
        return Response({"detail": "Thanks — a moderator will review this message."}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def hide(self, request, pk=None):
        message = self.get_object()
        if not can_moderate(request.user, message.group):
            raise PermissionDenied("Only moderators can hide messages.")
        message.is_hidden = True
        message.hidden_by = request.user
        message.save(update_fields=["is_hidden", "hidden_by"])
        message.reports.update(resolved=True, resolved_by=request.user)
        audit.record(request, "hide_message", message, group=message.group_id)
        return Response(MessageSerializer(message).data)


class ModerationViewSet(viewsets.ViewSet):
    """Admin queue of reported chat messages."""

    permission_classes = [IsPlatformAdmin]

    def list(self, request):
        reports = MessageReport.objects.filter(resolved=False).select_related(
            "message", "message__author", "message__group", "reporter"
        )
        return Response(
            [
                {
                    "id": r.id,
                    "reason": r.reason,
                    "reporter": r.reporter.display_name,
                    "created_at": r.created_at,
                    "message": {
                        "id": r.message_id,
                        "body": r.message.body,
                        "author": r.message.author.display_name if r.message.author else None,
                        "group": r.message.group.name,
                        "is_hidden": r.message.is_hidden,
                    },
                }
                for r in reports
            ]
        )

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        report = get_object_or_404(MessageReport, pk=pk)
        if request.data.get("hide"):
            report.message.is_hidden = True
            report.message.hidden_by = request.user
            report.message.save(update_fields=["is_hidden", "hidden_by"])
        MessageReport.objects.filter(message=report.message).update(resolved=True, resolved_by=request.user)
        audit.record(request, "resolve_report", report, hidden=bool(request.data.get("hide")))
        return Response({"resolved": True})
