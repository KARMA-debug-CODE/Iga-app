import ipaddress

from django.conf import settings

from .models import AuditLog


def _valid_ip(value):
    try:
        return str(ipaddress.ip_address(value.strip()))
    except (ValueError, AttributeError):
        return None


def client_ip(request):
    """The connecting client's IP, trusting X-Forwarded-For only for our own proxies.

    nginx appends the address it saw to X-Forwarded-For, so with N trusted proxies the
    client is the N-th entry from the right. Anything further left was sent by the client
    and could be forged.
    """
    if request is None:
        return None
    hops = settings.TRUSTED_PROXY_COUNT
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if hops > 0 and forwarded:
        parts = [p for p in forwarded.split(",") if p.strip()]
        if len(parts) >= hops:
            ip = _valid_ip(parts[-hops])
            if ip:
                return ip
    return _valid_ip(request.META.get("REMOTE_ADDR", ""))


def record(request, action, target, **details):
    """Write an audit entry. `target` is a model instance, or None for an event about no particular row
    (for example a failed sign-in to an account that doesn't exist)."""
    actor = getattr(request, "user", None)
    if actor is not None and not actor.is_authenticated:
        actor = None
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target._meta.label_lower if target is not None else "",
        target_id=str(target.pk) if target is not None else "",
        details=details,
        ip_address=client_ip(request),
    )
