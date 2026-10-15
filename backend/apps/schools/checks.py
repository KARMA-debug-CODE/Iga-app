"""Billing settings that would give subscriptions away on a real deployment stop it from starting.

`manage.py migrate` runs the system checks, so an Error here keeps the container from serving (see
apps/core/checks.py for what a "real deployment" is: DEBUG off with HTTPS on). A staging server that
takes test payments on purpose sets BILLING_ALLOW_TEST_PAYMENTS=true.
"""

from django.conf import settings
from django.core.checks import Error, Warning, register

from apps.core.checks import KNOWN_LOCAL_SECRETS, real_deployment

MIN_WEBHOOK_HASH_LENGTH = 16


@register()
def billing_test_payments_check(app_configs, **kwargs):
    if not real_deployment() or settings.BILLING_ALLOW_TEST_PAYMENTS:
        return []
    hint = (
        "Switch it off in .env. A staging server that should take test payments sets BILLING_ALLOW_TEST_PAYMENTS=true "
        "(never on the real one)."
    )
    errors = []
    if settings.BILLING_DEV_MODE:
        errors.append(
            Error(
                "BILLING_DEV_MODE is on: any school administrator can complete the test checkout and get paid months "
                "for nothing.",
                hint=hint,
                id="iga.E010",
            )
        )
    if settings.BILLING_PROVIDER == "flutterwave" and settings.FLUTTERWAVE_SECRET_KEY.startswith("FLWSECK_TEST"):
        errors.append(
            Error(
                "FLUTTERWAVE_SECRET_KEY is a test key: Flutterwave's published test cards would pay for real subscriptions.",
                hint="Use the live secret key (FLWSECK-...). " + hint,
                id="iga.E011",
            )
        )
    return errors


@register()
def billing_webhook_secret_check(app_configs, **kwargs):
    """Without a strong webhook secret Flutterwave's notifications are refused (or guessable)."""
    if not real_deployment() or settings.BILLING_PROVIDER != "flutterwave":
        return []
    secret = settings.FLUTTERWAVE_WEBHOOK_HASH
    if not secret:
        problem = "is not set, so every Flutterwave webhook is refused"
    elif len(secret) < MIN_WEBHOOK_HASH_LENGTH or secret in KNOWN_LOCAL_SECRETS:
        problem = "is short or a well-known value, so webhooks could be forged"
    else:
        return []
    return [
        Warning(
            f"FLUTTERWAVE_WEBHOOK_HASH {problem}; payments are then only confirmed when the payer comes back or by "
            "reconcile_payments.",
            hint='Set a long random value (python -c "import secrets; print(secrets.token_urlsafe(32))") in .env and the '
            "same one as the secret hash in Flutterwave's dashboard (Settings > Webhooks).",
            id="iga.W010",
        )
    ]
