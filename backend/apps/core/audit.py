from .models import AuditLog


def client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def record(request, action, target, **details):
    """Write an audit entry. `target` is a model instance."""
    actor = getattr(request, "user", None)
    if actor is not None and not actor.is_authenticated:
        actor = None
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target._meta.label_lower,
        target_id=str(target.pk),
        details=details,
        ip_address=client_ip(request),
    )
