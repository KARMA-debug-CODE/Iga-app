"""Keep issued refresh tokens out of the database in a usable form."""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken


def without_signature(token):
    """A JWT without its signature ("header.payload."): it still says whose token it was and until
    when, but can't be used to sign in."""
    head, dot, _ = str(token or "").rpartition(".")
    return f"{head}." if dot else ""


@receiver(pre_save, sender=OutstandingToken)
def store_refresh_tokens_unsigned(sender, instance, **kwargs):
    """simplejwt records every refresh token it issues, for rotation and logging out everywhere, which
    only need the token's id (jti). The whole token is a working session for 14 days, so a copy of the
    database (a backup, a leaked dump, the Django admin's token pages) would let anyone take over every
    signed-in account: only the unsigned part is kept."""
    instance.token = without_signature(instance.token)
