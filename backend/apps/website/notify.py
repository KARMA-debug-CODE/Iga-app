"""The email that tells the Iga team about a new contact-form message (CONTACT_EMAIL)."""

import logging

from django.conf import settings
from django.core.mail import EmailMessage

log = logging.getLogger(__name__)


def new_message(message_id):
    """Email CONTACT_EMAIL about one message. Runs after the answer has gone (password_reset.deliver)."""
    from .models import ContactMessage

    if not settings.CONTACT_EMAIL:
        return
    message = ContactMessage.objects.filter(pk=message_id).first()
    if message is None:
        return
    # The team reads these in English; the sender's text is quoted as they typed it (plain text, never HTML).
    body = "\n".join(
        [
            f"New message from the {settings.APP_NAME} contact form.",
            "",
            f"Name: {message.name}",
            f"Email: {message.email}",
            f"School: {message.school or '-'}",
            f"Language: {message.language}",
            f"Signed in as: {message.user.username if message.user_id else '-'}",
            "",
            message.message,
            "",
            f"Read and mark it as handled in Admin -> Messages: {settings.FRONTEND_URL}/admin",
        ]
    )
    email = EmailMessage(
        subject=f"{settings.APP_NAME} contact: {message.name}"[:150],
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.CONTACT_EMAIL],
        reply_to=[message.email],
    )
    try:
        email.send()
    except Exception:  # the message is stored; a mail problem must not lose it or reach the sender
        log.exception("Couldn't email contact message %s", message_id)
