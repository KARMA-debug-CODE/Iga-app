"""The money ledger: an append-only, hash-chained journal of every money event.

Every applied payment, free extension, refund and correction adds one `LedgerEntry`, in the same
database transaction as the change it records. Nothing ever changes or deletes an entry: the model
refuses it, the Django admin is read-only, and on PostgreSQL a trigger (migration 0005) refuses
UPDATE and DELETE on the table. A mistake is fixed by a new entry (a correction) that points at it.

Each entry stores `prev_hash`, the hash of the entry before it, and `entry_hash`, the hash of its
own fields plus `prev_hash` (SHA-256, or HMAC-SHA256 when LEDGER_HMAC_KEY is set, so that someone
who can write to the database but doesn't know the key can't rebuild the chain). `verify()` (the
`verify_ledger` command) recomputes the chain and checks every paid payment has its entry, so a
changed, removed, inserted or reordered entry is detected.

The fields that are hashed and how they are written (`hash_fields`) must never change: entries
already written would stop verifying.
"""

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import UTC
from decimal import Decimal

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from .models import LedgerEntry, Payment

GENESIS = "0" * 64
CENTS = Decimal("0.01")
# Any constant: the key of the PostgreSQL advisory lock that puts appends in a single line.
LOCK_KEY = 4_712_001


def _money(value) -> str:
    return str(Decimal(value or 0).quantize(CENTS))


def _moment(value) -> str:
    return value.astimezone(UTC).isoformat() if value else ""


def hash_fields(entry) -> dict:
    """What an entry's hash covers, as plain strings and numbers (works for historical models too)."""
    return {
        "v": 1,
        "sequence": int(entry.sequence),
        "kind": entry.kind,
        "school": int(entry.school_id),
        "payment": str(entry.payment_id or ""),
        "corrects": int(entry.corrects_id) if entry.corrects_id else 0,
        "currency": entry.currency,
        "gross": _money(entry.gross_amount),
        "fee": _money(entry.provider_fee),
        "net": _money(entry.net_amount),
        "months": int(entry.months),
        "paid_until_before": _moment(entry.paid_until_before),
        "paid_until_after": _moment(entry.paid_until_after),
        "reference": entry.reference,
        "actor": int(entry.actor_user_id) if entry.actor_user_id else 0,
        "actor_name": entry.actor_name,
        "note": entry.note,
        "idempotency_key": entry.idempotency_key,
        "created_at": _moment(entry.created_at),
    }


def compute_hash(fields: dict, prev_hash: str, alg: str, key: bytes = b"") -> str:
    payload = json.dumps({**fields, "prev_hash": prev_hash}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    if alg == "hmac-sha256":
        return hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hashlib.sha256(payload).hexdigest()


def _key() -> bytes:
    return settings.LEDGER_HMAC_KEY.encode()


def current_alg() -> str:
    return "hmac-sha256" if settings.LEDGER_HMAC_KEY else "sha256"


def _lock():
    """Appends go one at a time, so two can never claim the same place in the chain."""
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [LOCK_KEY])
    # SQLite allows one writer at a time anyway; the unique sequence and prev_hash are the backstop.


def append(
    kind,
    school,
    *,
    currency,
    gross,
    fee=Decimal("0"),
    months=0,
    paid_until_before=None,
    paid_until_after=None,
    payment=None,
    corrects=None,
    actor=None,
    reference="",
    note="",
    idempotency_key="",
    now=None,
) -> LedgerEntry:
    """Add one entry at the end of the chain. Call it inside the transaction that makes the change."""
    gross = Decimal(gross).quantize(CENTS)
    fee = Decimal(fee or 0).quantize(CENTS)
    with transaction.atomic():
        _lock()
        last = LedgerEntry.objects.order_by("-sequence").only("sequence", "entry_hash").first()
        entry = LedgerEntry(
            sequence=(last.sequence + 1) if last else 1,
            kind=kind,
            school=school,
            payment=payment,
            corrects=corrects,
            currency=currency,
            gross_amount=gross,
            provider_fee=fee,
            net_amount=gross - fee,
            months=months,
            paid_until_before=paid_until_before,
            paid_until_after=paid_until_after,
            reference=str(reference or "")[:100],
            actor_user_id=getattr(actor, "pk", None),
            actor_name=(getattr(actor, "username", "") or "")[:150],
            note=str(note or "")[:300],
            idempotency_key=idempotency_key or "",
            created_at=now or timezone.now(),
            hash_alg=current_alg(),
            prev_hash=last.entry_hash if last else GENESIS,
        )
        entry.entry_hash = compute_hash(hash_fields(entry), entry.prev_hash, entry.hash_alg, _key())
        entry._appending = True
        entry.save()
    return entry


@dataclass
class Report:
    entries: int = 0
    head_sequence: int = 0
    head_hash: str = GENESIS
    problems: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.problems


def verify(expect_head: str = "") -> Report:
    """Recompute the whole chain and cross-check it against the payments.

    Problems found: a gap or duplicate in the sequence, an entry whose hash or link doesn't match
    (it was edited, removed, inserted or reordered), an HMAC entry when no key is set (can't be
    checked), a plain-SHA-256 entry after an HMAC one (a downgrade), a paid payment without its
    entry or with a different amount, and a head that doesn't match `expect_head` ("SEQ:HASH",
    printed by an earlier run and kept somewhere else). A warning, not a problem: a key is set but
    the newest entry isn't signed with it (normal just after setting the key, until the next entry).
    """
    report = Report()
    previous = GENESIS
    expected_sequence = 1
    seen_hmac = False
    last_alg = ""
    key = _key()
    for entry in LedgerEntry.objects.order_by("sequence").iterator(chunk_size=500):
        report.entries += 1
        if entry.sequence != expected_sequence:
            report.problems.append(f"#{entry.sequence}: expected entry #{expected_sequence} here (missing or extra entries)")
            expected_sequence = entry.sequence
        if entry.prev_hash != previous:
            report.problems.append(f"#{entry.sequence}: does not follow the entry before it (prev_hash differs)")
        if entry.hash_alg == "hmac-sha256":
            seen_hmac = True
            if not key:
                report.problems.append(f"#{entry.sequence}: signed with LEDGER_HMAC_KEY, which is not set here")
        elif entry.hash_alg != "sha256" or seen_hmac:
            report.problems.append(f"#{entry.sequence}: unexpected hash algorithm {entry.hash_alg!r}")
        recomputed = compute_hash(hash_fields(entry), entry.prev_hash, entry.hash_alg, key)
        if not hmac.compare_digest(recomputed, entry.entry_hash):
            report.problems.append(f"#{entry.sequence}: its contents changed after it was written (hash differs)")
        if entry.net_amount != entry.gross_amount - entry.provider_fee:
            report.problems.append(f"#{entry.sequence}: net is not gross minus fee")
        previous = entry.entry_hash
        expected_sequence += 1
        report.head_sequence, report.head_hash = entry.sequence, entry.entry_hash
        last_alg = entry.hash_alg
    if key and report.entries and last_alg != "hmac-sha256":
        # Right after the key is set this is expected, until the next money event; otherwise the
        # chain may have been rebuilt without the key. --expect-head settles it.
        report.warnings.append("the newest entry is not signed with LEDGER_HMAC_KEY")

    recorded = {}
    for payment_id, gross, currency in LedgerEntry.objects.filter(
        kind__in=[LedgerEntry.Kind.PAYMENT, LedgerEntry.Kind.FREE_MONTHS], payment__isnull=False
    ).values_list("payment_id", "gross_amount", "currency"):
        recorded.setdefault(payment_id, []).append((gross, currency))
    for payment in Payment.objects.filter(status=Payment.Status.SUCCEEDED).only(
        "id", "reference", "amount", "gross_amount", "currency"
    ):
        rows = recorded.get(payment.id, [])
        if not rows:
            report.problems.append(f"payment {payment.reference}: paid but has no ledger entry")
        elif len(rows) > 1:
            report.problems.append(f"payment {payment.reference}: recorded {len(rows)} times in the ledger")
        else:
            gross, currency = rows[0]
            expected = payment.gross_amount if payment.gross_amount is not None else payment.amount
            if gross != Decimal(expected).quantize(CENTS) or currency != payment.currency:
                report.problems.append(f"payment {payment.reference}: amount differs from its ledger entry")

    if expect_head:
        if f"{report.head_sequence}:{report.head_hash}" != expect_head.strip():
            report.problems.append("the ledger's head is not the one expected (entries removed or the chain rebuilt)")
    return report
