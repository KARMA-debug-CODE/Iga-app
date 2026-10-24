"""School subscriptions: prices, payments and how a payment extends a school's access.

A school is "paid through" `School.paid_until`. A successful payment for N months extends it
by N calendar months, counted from today or from the current end date if that is later, so
renewing early never loses days. Payments are applied exactly once, inside a transaction that
locks the payment and school rows, whichever path reports them first (redirect, webhook or an
administrator), and each applied payment, refund or correction adds an entry to the money
ledger (ledger.py) in that same transaction.

Prices, plans and durations come only from settings (SUBSCRIPTION_PRICES, SUBSCRIPTION_MONTH_OPTIONS):
a client chooses one of the offered month counts and currencies, and anything else it sends
(an amount, a price, a plan, a number of days) is ignored.
"""

import calendar
import logging
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import APIException, ValidationError

from . import ledger
from .models import LedgerEntry, Payment, School

log = logging.getLogger(__name__)

# Currencies without a minor unit: prices are whole francs.
ZERO_DECIMAL_CURRENCIES = {"RWF"}


def add_months(moment: datetime, months: int) -> datetime:
    """Same day-of-month N months later, clamped to the month's last day (31 Jan + 1 = 28/29 Feb)."""
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def currencies():
    return list(settings.SUBSCRIPTION_PRICES)


def price_list():
    """The prices schools are offered, from the settings: what the school's billing page and the public
    pricing section both show (so a price is never written down twice)."""
    return {
        "prices": {currency: str(amount) for currency, amount in settings.SUBSCRIPTION_PRICES.items()},
        "month_options": settings.SUBSCRIPTION_MONTH_OPTIONS,
        "grace_days": settings.SUBSCRIPTION_GRACE_DAYS,
    }


def finite_amount(value):
    """A Decimal for a finite number, else None (NaN, Infinity and anything unreadable)."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return amount if amount.is_finite() else None


class PriceNotConfigured(APIException):
    status_code = 503
    default_code = "price_not_configured"

    def __init__(self):
        super().__init__(_("Online payment isn't set up correctly yet. Please contact the Iga team."))


def price(months: int, currency: str) -> Decimal:
    if months not in settings.SUBSCRIPTION_MONTH_OPTIONS:
        raise ValidationError(
            {"months": _("Choose %(options)s months.") % {"options": ", ".join(map(str, settings.SUBSCRIPTION_MONTH_OPTIONS))}}
        )
    if currency not in settings.SUBSCRIPTION_PRICES:
        raise ValidationError(
            {"currency": _("Choose one of these currencies: %(options)s.") % {"options": ", ".join(currencies())}}
        )
    unit = finite_amount(settings.SUBSCRIPTION_PRICES[currency])
    if unit is None or unit <= 0:
        # A missing, zero or garbled price must never turn into a free (or negative) checkout.
        log.error("SUBSCRIPTION_PRICES[%s] is not a positive number: %r", currency, settings.SUBSCRIPTION_PRICES[currency])
        raise PriceNotConfigured()
    step = Decimal("1") if currency in ZERO_DECIMAL_CURRENCIES else Decimal("0.01")
    return (unit * months).quantize(step)


def new_reference():
    return f"iga-{secrets.token_hex(12)}"


def start_payment(school: School, user, months: int, currency: str, provider: str) -> Payment:
    if not school.is_verified:
        raise ValidationError(_("Your school must be verified by the Iga team before it can subscribe."))
    return Payment.objects.create(
        reference=new_reference(),
        school=school,
        created_by=user,
        provider=provider,
        months=months,
        amount=price(months, currency),
        currency=currency,
    )


class TransactionAlreadyUsed(Exception):
    """The provider transaction already paid for another payment, so it can't pay for this one."""


def money_for(payment, gross=None, fee=None):
    """(gross, provider fee, net) for an applied payment, worked out on the server.

    gross: what the payer was charged, as the provider's verified answer says (otherwise the
    payment's own price); fee: the provider's fee from that same answer, or 0 when it gives none or
    a value that makes no sense; net = gross - fee, what reaches Iga's account.
    """
    gross = finite_amount(gross)
    if gross is None or gross < 0:
        gross = Decimal(payment.amount)
    fee = finite_amount(fee)
    if fee is None or fee < 0 or fee > gross:
        if fee is not None:
            log.warning("Ignoring an impossible provider fee %s for payment %s", fee, payment.reference)
        fee = Decimal("0")
    cents = Decimal("0.01")
    gross, fee = gross.quantize(cents), fee.quantize(cents)
    return gross, fee, gross - fee


def apply_payment(
    payment: Payment, transaction_id: str = "", data: dict | None = None, now=None, *, gross=None, fee=None, actor=None
) -> bool:
    """Mark a payment as paid, extend the school's subscription and write it in the ledger.

    Only ever called once the provider's own API has confirmed the money arrived (or for a payment
    an administrator recorded), so it also applies to a payment already marked failed or
    cancelled: a success reported late, after the checkout closed, must still give the school its
    months. Returns True if this call applied it, False if it had already been applied. Raises
    TransactionAlreadyUsed if the provider transaction already paid for another payment.
    """
    now = now or timezone.now()
    transaction_id = str(transaction_id or "")[:100]
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status == Payment.Status.SUCCEEDED:
            return False
        if (
            transaction_id
            and Payment.objects.filter(provider=payment.provider, provider_transaction_id=transaction_id)
            .exclude(pk=payment.pk)
            .exists()
        ):
            log.error(
                "Provider transaction %s already paid for another payment; not applying %s", transaction_id, payment.reference
            )
            raise TransactionAlreadyUsed(transaction_id)
        school = School.objects.select_for_update().get(pk=payment.school_id)
        before = school.paid_until
        start = max(now, school.paid_until) if school.paid_until else now
        # Calendar months in Kigali time: a payment just after midnight belongs to the new day.
        end = add_months(timezone.localtime(start), payment.months)
        school.paid_until = end
        school.save(update_fields=["paid_until"])
        payment.status = Payment.Status.SUCCEEDED
        payment.paid_at = now
        payment.period_start = start
        payment.period_end = end
        payment.gross_amount, payment.provider_fee, payment.net_amount = money_for(payment, gross, fee)
        if transaction_id:
            payment.provider_transaction_id = transaction_id
        if data is not None:
            payment.provider_data = data
        payment.save()
        ledger.append(
            LedgerEntry.Kind.PAYMENT if payment.gross_amount > 0 else LedgerEntry.Kind.FREE_MONTHS,
            school,
            payment=payment,
            currency=payment.currency,
            gross=payment.gross_amount,
            fee=payment.provider_fee,
            months=payment.months,
            paid_until_before=before,
            paid_until_after=end,
            reference=payment.provider_transaction_id or payment.external_reference or payment.reference,
            actor=actor,
            note=payment.note,
            now=now,
        )
    return True


def fail_payment(payment: Payment, status: str = Payment.Status.FAILED, data: dict | None = None) -> bool:
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != Payment.Status.PENDING:
            return False
        payment.status = status
        if data is not None:
            payment.provider_data = data
        payment.save(update_fields=["status", "provider_data"])
    return True


class IdempotencyConflict(APIException):
    status_code = 409
    default_code = "idempotency_conflict"

    def __init__(self):
        super().__init__(_("This request key was already used for a different request."))


def normalise_reference(value: str) -> str:
    """Bank and receipt references compared without case or extra spaces."""
    return " ".join(str(value or "").split()).upper()[:100]


def _already_recorded(reference):
    earlier = Payment.objects.select_related("school").filter(external_reference=reference).first()
    when = timezone.localtime(earlier.created_at).date().isoformat() if earlier else ""
    return ValidationError(
        {
            "external_reference": _("This reference was already recorded on %(date)s for %(school)s.")
            % {"date": when, "school": earlier.school.name if earlier else ""}
        }
    )


def record_manual_payment_once(
    school: School,
    admin,
    months: int,
    amount: Decimal,
    currency: str,
    note: str,
    *,
    external_reference: str = "",
    idempotency_key: str = "",
):
    """A platform administrator records money received outside the app (bank transfer, cash,
    mobile money to the company account) or a complimentary extension (amount 0).

    Returns (payment, created). A request resent with the same Idempotency-Key returns the payment
    it recorded the first time (created False), and a bank or receipt reference can only be
    recorded once, so the same transfer never extends a subscription twice, even when two
    requests arrive at the same moment (unique constraints decide which one wins).
    """
    if months < 1 or months > 24:
        raise ValidationError({"months": _("Between 1 and 24 months.")})
    amount = finite_amount(amount)
    if amount is None or amount < 0:
        raise ValidationError({"amount": _("The amount can't be negative.")})
    if not note.strip():
        raise ValidationError({"note": _("Say how it was paid (bank reference, receipt number, or why it is free).")})
    reference = normalise_reference(external_reference)

    def replay():
        earlier = Payment.objects.filter(created_by=admin, idempotency_key=idempotency_key).first()
        if earlier is None:
            return None
        same = (earlier.school_id, earlier.months, Decimal(earlier.amount), earlier.currency, earlier.external_reference) == (
            school.pk,
            months,
            amount.quantize(Decimal("0.01")),
            currency,
            reference,
        )
        if not same:
            raise IdempotencyConflict()
        return earlier

    if idempotency_key and (earlier := replay()) is not None:
        return earlier, False
    if reference and Payment.objects.filter(external_reference=reference).exists():
        raise _already_recorded(reference)
    try:
        with transaction.atomic():
            payment = Payment.objects.create(
                reference=new_reference(),
                school=school,
                created_by=admin,
                provider=Payment.Provider.MANUAL,
                months=months,
                amount=amount,
                currency=currency,
                note=note.strip()[:300],
                external_reference=reference,
                idempotency_key=idempotency_key,
            )
            apply_payment(payment, actor=admin)
    except IntegrityError:
        # Another request with the same key or reference was recorded a moment before this one.
        if idempotency_key and (earlier := replay()) is not None:
            return earlier, False
        if reference:
            raise _already_recorded(reference)
        raise
    payment.refresh_from_db()
    return payment, True


def record_manual_payment(school: School, admin, months: int, amount: Decimal, currency: str, note: str, **kwargs) -> Payment:
    return record_manual_payment_once(school, admin, months, amount, currency, note, **kwargs)[0]


def record_correction(
    school: School,
    actor,
    kind: str,
    currency: str,
    gross,
    note: str,
    *,
    fee=Decimal("0"),
    months: int = 0,
    corrects: LedgerEntry | None = None,
    idempotency_key: str = "",
    now=None,
):
    """A refund or a correction: a new ledger entry (entries are never changed), and the school's
    paid-through date moved by `months` (negative to take months back). Returns (entry, created)."""
    if kind not in (LedgerEntry.Kind.REFUND, LedgerEntry.Kind.CORRECTION):
        raise ValidationError({"kind": _("Choose a refund or a correction.")})
    gross, fee = finite_amount(gross), finite_amount(fee)
    if gross is None or fee is None:
        raise ValidationError({"amount": _("Enter a number.")})
    if kind == LedgerEntry.Kind.REFUND and gross >= 0:
        raise ValidationError({"amount": _("A refund is money paid back: enter it as a negative amount.")})
    if fee < 0 or abs(fee) > abs(gross):
        raise ValidationError({"provider_fee": _("The fee must be between 0 and the amount.")})
    if not -24 <= months <= 24:
        raise ValidationError({"months": _("Between -24 and 24 months.")})
    if gross == 0 and months == 0:
        raise ValidationError({"amount": _("A correction must change an amount or a number of months.")})
    if not note.strip():
        raise ValidationError({"note": _("Say why (for example the refund reference or what was wrong).")})
    if corrects is not None and corrects.school_id != school.pk:
        raise ValidationError({"corrects": _("That entry belongs to another school.")})
    now = now or timezone.now()

    def replay():
        earlier = LedgerEntry.objects.filter(actor_user_id=actor.pk, idempotency_key=idempotency_key).first()
        if earlier is not None and (earlier.school_id, earlier.kind, earlier.gross_amount, earlier.months) != (
            school.pk,
            kind,
            gross.quantize(Decimal("0.01")),
            months,
        ):
            raise IdempotencyConflict()
        return earlier

    if idempotency_key and (earlier := replay()) is not None:
        return earlier, False
    try:
        with transaction.atomic():
            school = School.objects.select_for_update().get(pk=school.pk)
            before = school.paid_until
            after = before
            if months:
                if months < 0 and before is None:
                    raise ValidationError({"months": _("This school has no paid months to take back.")})
                start = before if months < 0 else (max(now, before) if before else now)
                after = add_months(timezone.localtime(start), months)
                school.paid_until = after
                school.save(update_fields=["paid_until"])
            entry = ledger.append(
                kind,
                school,
                currency=currency,
                gross=gross,
                fee=fee,
                months=months,
                paid_until_before=before,
                paid_until_after=after,
                payment=corrects.payment if corrects is not None else None,
                corrects=corrects,
                actor=actor,
                note=note.strip(),
                idempotency_key=idempotency_key,
                now=now,
            )
    except IntegrityError:
        if idempotency_key and (earlier := replay()) is not None:
            return earlier, False
        raise
    return entry, True


def _audit_rejection(request, payment, reason, transaction_id):
    """Keep a refused verification in the audit log, once per payment, reason and transaction."""
    from apps.core import audit
    from apps.core.models import AuditLog

    already = AuditLog.objects.filter(
        action="payment_rejected", target_type=payment._meta.label_lower, target_id=str(payment.pk)
    ).filter(details__reason=reason, details__transaction_id=str(transaction_id or ""))
    if not already.exists():
        audit.record(request, "payment_rejected", payment, reason=reason, transaction_id=str(transaction_id or ""))


def settle(payment: Payment, verification, request=None) -> Payment:
    """Act on what the provider says about a payment. Safe to call any number of times."""
    from apps.core import audit

    from . import notify

    if verification.status == "succeeded":
        try:
            applied = apply_payment(
                payment, verification.transaction_id, verification.data, gross=verification.gross, fee=verification.fee
            )
        except TransactionAlreadyUsed:
            _audit_rejection(request, payment, "transaction_reused", verification.transaction_id)
            applied = False
        if applied:
            payment.refresh_from_db()
            audit.record(
                request,
                "subscription_paid",
                payment.school,
                reference=payment.reference,
                months=payment.months,
                amount=str(payment.amount),
                currency=payment.currency,
                provider=payment.provider,
                gross=str(payment.gross_amount),
                provider_fee=str(payment.provider_fee),
                net=str(payment.net_amount),
            )
            notify.payment_received(payment)
    elif verification.status == "failed":
        fail_payment(payment, data=verification.data)
        if verification.reason:
            _audit_rejection(request, payment, verification.reason, verification.transaction_id)
    payment.refresh_from_db()
    return payment
