"""The money ledger is append-only in the database itself, and starts with the payments made before it.

On PostgreSQL a trigger refuses every UPDATE and DELETE on schools_ledgerentry, whoever the database
user is (only someone who can drop or disable the trigger, i.e. the table's owner, gets past it, and
that is a schema change). TRUNCATE is not blocked here, because the test suite empties tables that
way; the role the app runs as has no TRUNCATE privilege (`manage.py db_roles`), and `verify_ledger`
reports paid payments that have lost their entry.

Payments already paid get their gross, fee and net, and one ledger entry each, oldest first.
"""

from decimal import Decimal

from django.db import migrations


def add_trigger(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            """
CREATE OR REPLACE FUNCTION schools_ledgerentry_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'schools_ledgerentry is append-only: % refused (record a correction instead)', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS schools_ledgerentry_append_only ON schools_ledgerentry;
CREATE TRIGGER schools_ledgerentry_append_only
    BEFORE UPDATE OR DELETE ON schools_ledgerentry
    FOR EACH ROW EXECUTE FUNCTION schools_ledgerentry_append_only();
""",
            params=None,
        )


def drop_trigger(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            """
DROP TRIGGER IF EXISTS schools_ledgerentry_append_only ON schools_ledgerentry;
DROP FUNCTION IF EXISTS schools_ledgerentry_append_only();
""",
            params=None,
        )


def _finite(value):
    try:
        amount = Decimal(str(value))
    except Exception:
        return None
    return amount if amount.is_finite() else None


def backfill(apps, schema_editor):
    from django.conf import settings

    from apps.schools.ledger import GENESIS, compute_hash, hash_fields

    Payment = apps.get_model("schools", "Payment")
    LedgerEntry = apps.get_model("schools", "LedgerEntry")
    if LedgerEntry.objects.exists():
        return
    alg = "hmac-sha256" if settings.LEDGER_HMAC_KEY else "sha256"
    key = settings.LEDGER_HMAC_KEY.encode()
    cents = Decimal("0.01")
    previous, sequence = GENESIS, 0
    for payment in Payment.objects.filter(status="succeeded").order_by("paid_at", "created_at", "reference"):
        data = payment.provider_data if isinstance(payment.provider_data, dict) else {}
        gross = Decimal(payment.amount)
        if payment.provider == "flutterwave":
            amount, charged = _finite(data.get("amount")), _finite(data.get("charged_amount"))
            gross = charged if charged is not None and amount is not None and charged >= amount else (amount or gross)
        fee = _finite(data.get("app_fee")) if payment.provider == "flutterwave" else None
        if fee is None or fee < 0 or fee > gross:
            fee = Decimal("0")
        gross, fee = gross.quantize(cents), fee.quantize(cents)
        Payment.objects.filter(pk=payment.pk).update(gross_amount=gross, provider_fee=fee, net_amount=gross - fee)
        sequence += 1
        entry = LedgerEntry(
            sequence=sequence,
            kind="payment" if gross > 0 else "free_months",
            school_id=payment.school_id,
            payment_id=payment.pk,
            currency=payment.currency,
            gross_amount=gross,
            provider_fee=fee,
            net_amount=gross - fee,
            months=payment.months,
            paid_until_before=payment.period_start,
            paid_until_after=payment.period_end,
            reference=(payment.provider_transaction_id or payment.reference)[:100],
            note="Recorded before the ledger existed",
            created_at=payment.paid_at or payment.created_at,
            hash_alg=alg,
            prev_hash=previous,
        )
        entry.entry_hash = compute_hash(hash_fields(entry), previous, alg, key)
        entry.save(force_insert=True)
        previous = entry.entry_hash


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0004_money_ledger"),
    ]

    operations = [
        migrations.RunPython(add_trigger, drop_trigger),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
