from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.schools import billing
from apps.schools.models import Payment, School

pytestmark = pytest.mark.django_db

UTC = UTC


@pytest.mark.parametrize(
    ("start", "months", "expected"),
    [
        (datetime(2026, 1, 15, 9, 30, tzinfo=UTC), 1, datetime(2026, 2, 15, 9, 30, tzinfo=UTC)),
        (datetime(2026, 1, 31, tzinfo=UTC), 1, datetime(2026, 2, 28, tzinfo=UTC)),
        (datetime(2028, 1, 31, tzinfo=UTC), 1, datetime(2028, 2, 29, tzinfo=UTC)),  # leap year
        (datetime(2026, 11, 30, tzinfo=UTC), 3, datetime(2027, 2, 28, tzinfo=UTC)),
        (datetime(2026, 5, 10, tzinfo=UTC), 12, datetime(2027, 5, 10, tzinfo=UTC)),
    ],
)
def test_add_months(start, months, expected):
    assert billing.add_months(start, months) == expected


def make_school(**extra):
    defaults = {"name": "Lycée de Kigali", "district": "Nyarugenge", "status": School.Status.VERIFIED}
    defaults.update(extra)
    return School.objects.create(**defaults)


def test_price_follows_settings(settings):
    settings.SUBSCRIPTION_PRICES = {"USD": Decimal("200"), "RWF": Decimal("280000")}
    assert billing.price(1, "USD") == Decimal("200.00")
    assert billing.price(12, "RWF") == Decimal("3360000.00")
    with pytest.raises(ValidationError):
        billing.price(2, "USD")  # not an offered option
    with pytest.raises(ValidationError):
        billing.price(1, "EUR")


def test_payment_extends_from_today_or_from_current_end():
    school = make_school()
    now = timezone.now()
    first = billing.start_payment(school, None, 1, "USD", Payment.Provider.DEV)
    assert billing.apply_payment(first, now=now)
    school.refresh_from_db()
    assert school.paid_until == billing.add_months(now, 1)

    # Renewing early adds to the end date, so no days are lost.
    second = billing.start_payment(school, None, 3, "USD", Payment.Provider.DEV)
    billing.apply_payment(second, now=now + timedelta(days=5))
    school.refresh_from_db()
    assert school.paid_until == billing.add_months(billing.add_months(now, 1), 3)
    second.refresh_from_db()
    assert second.period_start == billing.add_months(now, 1) and second.period_end == school.paid_until


def test_renewing_after_expiry_starts_from_today():
    long_ago = timezone.now() - timedelta(days=90)
    school = make_school(paid_until=long_ago)
    payment = billing.start_payment(school, None, 1, "USD", Payment.Provider.DEV)
    now = timezone.now()
    billing.apply_payment(payment, now=now)
    school.refresh_from_db()
    assert school.paid_until == billing.add_months(now, 1)


def test_a_payment_is_applied_only_once():
    school = make_school()
    payment = billing.start_payment(school, None, 1, "USD", Payment.Provider.DEV)
    assert billing.apply_payment(payment) is True
    school.refresh_from_db()
    once = school.paid_until
    assert billing.apply_payment(payment) is False
    school.refresh_from_db()
    assert school.paid_until == once
    assert billing.fail_payment(payment) is False  # can't fail a paid payment


def test_unverified_schools_cannot_pay():
    school = make_school(status=School.Status.PENDING)
    with pytest.raises(ValidationError):
        billing.start_payment(school, None, 1, "USD", Payment.Provider.DEV)


def test_subscription_states_and_grace(settings):
    settings.SUBSCRIPTION_GRACE_DAYS = 3
    now = timezone.now()
    school = make_school()
    assert school.subscription_state(now) == "none" and not school.subscription_active(now)
    school.paid_until = now + timedelta(days=1)
    assert school.subscription_state(now) == "active" and school.subscription_active(now)
    school.paid_until = now - timedelta(days=1)
    assert school.subscription_state(now) == "grace" and school.subscription_active(now)
    school.paid_until = now - timedelta(days=4)
    assert school.subscription_state(now) == "expired" and not school.subscription_active(now)
    school.paid_until = now + timedelta(days=10)
    school.status = School.Status.SUSPENDED
    assert not school.subscription_active(now)


def test_manual_payments_need_a_note_and_apply_immediately():
    school = make_school()
    with pytest.raises(ValidationError):
        billing.record_manual_payment(school, None, 1, Decimal("200"), "USD", "  ")
    payment = billing.record_manual_payment(school, None, 2, Decimal("0"), "USD", "Pilot school: two free months")
    assert payment.status == Payment.Status.SUCCEEDED
    school.refresh_from_db()
    assert school.subscription_active()
