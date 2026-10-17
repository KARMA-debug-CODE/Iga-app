"""The contact form's part of "Download my data" and "Delete my account" (apps/accounts/privacy.py)."""

from django.db.models import Q

from apps.core.exporting import iso

from .models import ContactMessage


def _mine(user):
    match = Q(user=user)
    if user.email:
        match |= Q(email__iexact=user.email)
    return match


def export_for(user):
    return {
        "contact_messages": [
            {"name": m.name, "email": m.email, "school": m.school, "message": m.message, "sent_at": iso(m.created_at)}
            for m in ContactMessage.objects.filter(_mine(user)).order_by("created_at")
        ]
    }


def erase_for(user):
    ContactMessage.objects.filter(_mine(user)).delete()
