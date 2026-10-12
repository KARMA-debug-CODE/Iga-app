"""What happens to each payment-provider webhook delivery: refused ones are logged and audited, and
an event that was already handled is recognised when it comes again (a replay) and not acted on.

A delivery is identified by the SHA-256 of its body once its signature is valid. The same body
again is a replay: it is acknowledged without asking the provider anything, unless its first
delivery could not reach a final answer (the provider was unreachable, or the transaction was still
pending), in which case it may be processed again once RETRY_AFTER has passed, because the
provider legitimately retries those. Applying a payment stays exactly-once whatever happens here
(billing.apply_payment locks the rows); this guard stops replays from making us call the provider
again and again, and keeps a trail of them.
"""

import hashlib
import logging
from datetime import timedelta

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.core import audit

from .models import WebhookEvent

log = logging.getLogger(__name__)
RETRY_AFTER = timedelta(seconds=60)
# Every refusal goes to the server log; at most this many a minute per address also go to the
# audit log, so a flood of forged requests can't fill the database.
AUDITED_REFUSALS_PER_MINUTE = 30


def digest(body: bytes) -> str:
    return hashlib.sha256(body or b"").hexdigest()


def _within_audit_budget(provider, ip):
    key = f"webhook-refusals:{provider}:{ip or '-'}"
    cache.add(key, 0, 60)
    try:
        return cache.incr(key) <= AUDITED_REFUSALS_PER_MINUTE
    except ValueError:  # the key expired between add and incr
        return True


def refuse(request, provider, outcome, body=b""):
    """A delivery we won't act on (bad signature, unreadable body): log it, and audit it."""
    ip = audit.client_ip(request)
    log.warning("Refused a %s webhook from %s: %s", provider, ip or "?", outcome)
    if not _within_audit_budget(provider, ip):
        return None
    event = WebhookEvent.objects.create(
        provider=provider,
        digest=digest(body),
        signature_valid=outcome != WebhookEvent.Outcome.BAD_SIGNATURE,
        outcome=outcome,
        ip_address=ip,
        processed_at=timezone.now(),
    )
    audit.record(request, "webhook_rejected", event, provider=provider, reason=outcome)
    return event


def claim(request, provider, body, reference="", transaction_id=""):
    """(event, fresh) for a delivery with a valid signature. fresh is False for a replay of an
    event that was already handled, or that another request is handling right now."""
    now = timezone.now()
    body_digest = digest(body)
    try:
        with transaction.atomic():
            event = WebhookEvent.objects.create(
                provider=provider,
                digest=body_digest,
                signature_valid=True,
                reference=str(reference)[:64],
                transaction_id=str(transaction_id)[:40],
                ip_address=audit.client_ip(request),
                claimed_at=now,
            )
        return event, True
    except IntegrityError:
        pass
    event = WebhookEvent.objects.get(provider=provider, digest=body_digest, signature_valid=True)
    WebhookEvent.objects.filter(pk=event.pk).update(deliveries=F("deliveries") + 1)
    # A conditional update, so of two copies arriving together only one goes on.
    taken = WebhookEvent.objects.filter(pk=event.pk, outcome__in=WebhookEvent.RETRYABLE, claimed_at__lt=now - RETRY_AFTER).update(
        claimed_at=now, outcome=WebhookEvent.Outcome.PROCESSING
    )
    event.refresh_from_db()
    if not taken:
        ip = audit.client_ip(request)
        log.warning("Ignored a replayed %s webhook for %s (delivery %s)", provider, event.reference or "-", event.deliveries)
        if _within_audit_budget(provider, ip):
            audit.record(
                request, "webhook_replayed", event, provider=provider, reference=event.reference, deliveries=event.deliveries
            )
    return event, bool(taken)


def finish(event, outcome, payment=None):
    WebhookEvent.objects.filter(pk=event.pk).update(outcome=outcome, payment=payment, processed_at=timezone.now())
