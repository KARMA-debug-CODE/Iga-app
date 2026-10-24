"""The study groups' part of "Download my data" and "Delete my account" (apps/accounts/privacy.py)."""

from django.db import transaction

from apps.core.exporting import iso

from .models import GroupMembership, Message, MessageReport, SharedNote, StudyGroup


def export_for(user):
    return {
        "groups": [
            {"group": m.group.name, "role": m.role, "joined_at": iso(m.joined_at)}
            for m in GroupMembership.objects.filter(user=user).select_related("group").order_by("joined_at")
        ],
        "messages": [
            {"group": m.group.name, "text": m.body, "hidden": m.is_hidden, "sent_at": iso(m.created_at)}
            for m in Message.objects.filter(author=user).select_related("group").order_by("created_at")
        ],
        "notes": [
            {"group": n.group.name, "title": n.title, "text": n.body, "created_at": iso(n.created_at)}
            for n in SharedNote.objects.filter(author=user).select_related("group").order_by("created_at")
        ],
        "reports_made": [
            {"reason": r.reason, "resolved": r.resolved, "created_at": iso(r.created_at)}
            for r in MessageReport.objects.filter(reporter=user).order_by("created_at")
        ],
    }


def erase_for(user):
    """The user's messages, notes and memberships go. Two things stay for the moderators while a report about
    them is open (safeguarding): a reported message, and a report the user made (both then show "Deleted
    account"); resolved reports the user made go."""
    Message.objects.filter(author=user).exclude(reports__resolved=False).delete()
    SharedNote.objects.filter(author=user).delete()
    MessageReport.objects.filter(reporter=user, resolved=True).delete()
    for membership in GroupMembership.objects.filter(user=user).select_related("group"):
        group = membership.group
        # As when a member leaves (views.StudyGroupViewSet.leave): the last one out deletes the group, and the
        # longest-standing member becomes the owner so the group stays moderated.
        with transaction.atomic():
            StudyGroup.objects.select_for_update().filter(pk=group.pk).first()
            membership.delete()
            if not group.memberships.exists():
                group.delete()
                continue
            if not group.memberships.filter(role=GroupMembership.Role.OWNER).exists():
                successor = group.memberships.order_by("joined_at", "id").first()
                GroupMembership.objects.filter(pk=successor.pk).update(role=GroupMembership.Role.OWNER)
