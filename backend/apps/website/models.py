from django.conf import settings
from django.db import models


class ContactMessage(models.Model):
    """A message sent with the public contact form. Platform admins read it in Admin -> Messages (and the
    Django admin); it is also emailed to CONTACT_EMAIL when that is set. Kept CONTACT_RETENTION_DAYS."""

    name = models.CharField(max_length=120)
    email = models.EmailField(max_length=254)
    school = models.CharField(max_length=200, blank=True)
    message = models.TextField(max_length=5000)
    # The language the form was shown in, so the answer can be written in it.
    language = models.CharField(max_length=2, default="en")
    # The account that sent it, when the sender was signed in.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    handled_at = models.DateTimeField(null=True, blank=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}> · {self.created_at:%Y-%m-%d %H:%M}"
