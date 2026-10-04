"""Flutterwave (cards and mobile money in Rwanda) through its v3 REST API, without an SDK.

Flow: create a hosted checkout link for our reference (tx_ref) -> the school administrator pays
on Flutterwave -> Flutterwave redirects back and also calls our webhook -> in both cases we ask
Flutterwave's API for the transaction by our reference and only apply the payment if it is
successful for the expected amount and currency.

Settings (environment):
  FLUTTERWAVE_SECRET_KEY   secret API key (FLWSECK-..., or FLWSECK_TEST-... in test mode)
  FLUTTERWAVE_WEBHOOK_HASH the "secret hash" set in the Flutterwave dashboard for webhooks
  FLUTTERWAVE_BASE_URL     defaults to https://api.flutterwave.com/v3
"""

import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation

from django.conf import settings
from rest_framework.exceptions import APIException

from .providers import Verification, return_url

log = logging.getLogger(__name__)
TIMEOUT_SECONDS = 20
PAYMENT_OPTIONS = {"USD": "card", "RWF": "card,mobilemoneyrwanda"}


class ProviderUnavailable(APIException):
    status_code = 503
    default_detail = "The payment service isn't answering right now. Please try again in a few minutes."
    default_code = "provider_unavailable"


def _request(method, path, payload=None):
    """One HTTP call to Flutterwave. Returns the decoded JSON body (tests replace this function)."""
    url = settings.FLUTTERWAVE_BASE_URL.rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            return json.loads(body)
        except ValueError:
            log.warning("Flutterwave %s %s failed: %s %s", method, path, exc.code, body[:300])
            raise ProviderUnavailable()
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        log.warning("Flutterwave %s %s unreachable: %s", method, path, exc)
        raise ProviderUnavailable()


def _amount(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


class FlutterwaveProvider:
    key = "flutterwave"

    def available(self):
        return bool(settings.FLUTTERWAVE_SECRET_KEY)

    def create_checkout(self, payment, user, request=None):
        school = payment.school
        payload = {
            "tx_ref": payment.reference,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "redirect_url": return_url(payment),
            "payment_options": PAYMENT_OPTIONS.get(payment.currency, "card"),
            "customer": {
                "email": user.email or school.email or settings.BILLING_FALLBACK_EMAIL,
                "name": user.display_name,
                "phonenumber": school.phone,
            },
            "customizations": {
                "title": f"{settings.APP_NAME} school subscription",
                "description": f"{school.name}: {payment.months} month(s)",
            },
            "meta": {"school_id": school.id, "months": payment.months},
        }
        body = _request("POST", "/payments", payload)
        link = (body.get("data") or {}).get("link") if body.get("status") == "success" else None
        if not link:
            log.warning("Flutterwave refused checkout for %s: %s", payment.reference, body.get("message"))
            raise ProviderUnavailable(body.get("message") or ProviderUnavailable.default_detail)
        return link

    def verify(self, payment):
        """Look the transaction up by our reference and check it really paid what we asked."""
        query = urllib.parse.urlencode({"tx_ref": payment.reference})
        body = _request("GET", f"/transactions/verify_by_reference?{query}")
        data = body.get("data") or {}
        if body.get("status") != "success" or not data:
            return Verification("pending", data=body)
        status = str(data.get("status", "")).lower()
        if status == "successful":
            amount = _amount(data.get("amount"))
            ok = (
                data.get("tx_ref") == payment.reference
                and str(data.get("currency", "")).upper() == payment.currency
                and amount is not None
                and amount >= payment.amount
            )
            if ok:
                return Verification("succeeded", str(data.get("id", "")), data)
            log.error("Flutterwave amount/currency mismatch for %s: %s", payment.reference, data)
            return Verification("failed", str(data.get("id", "")), data)
        if status in ("failed", "cancelled"):
            return Verification("failed", str(data.get("id", "")), data)
        return Verification("pending", str(data.get("id", "")), data)

    @staticmethod
    def webhook_is_authentic(request):
        """Flutterwave signs webhooks with the dashboard's secret hash: either the legacy
        `verif-hash` header (the hash itself) or `flutterwave-signature` (HMAC-SHA256 of the body)."""
        secret = settings.FLUTTERWAVE_WEBHOOK_HASH
        if not secret:
            return False
        legacy = request.headers.get("verif-hash")
        if legacy:
            return hmac.compare_digest(legacy, secret)
        signature = request.headers.get("flutterwave-signature")
        if signature:
            digest = hmac.new(secret.encode(), request.body, hashlib.sha256).digest()
            expected = base64.b64encode(digest).decode()
            return hmac.compare_digest(signature, expected) or hmac.compare_digest(signature, digest.hex())
        return False

    @staticmethod
    def webhook_reference(payload):
        data = payload.get("data") if isinstance(payload, dict) else None
        return (data or {}).get("tx_ref") or ""
