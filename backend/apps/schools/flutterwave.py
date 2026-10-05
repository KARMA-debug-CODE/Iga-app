"""Flutterwave (cards and mobile money in Rwanda) through its v3 REST API, without an SDK.

Flow: create a hosted checkout link for our reference (tx_ref) -> the school administrator pays
on Flutterwave -> Flutterwave redirects back and also calls our webhook -> in both cases we ask
Flutterwave's API about the transaction (by the id we were given, else by our reference) and only
apply the payment if it is successful for our reference, the expected currency and at least the
expected amount.

One checkout can hold several attempts: when a card is declined, the hosted page lets the payer
try again with the same tx_ref until the session ends. A failed attempt is therefore not a failed
payment while the session is open, and a successful transaction is applied whenever it is reported
(see billing.apply_payment), so a school that paid always gets its months.

Settings (environment):
  FLUTTERWAVE_SECRET_KEY   secret API key (FLWSECK-..., or FLWSECK_TEST-... in test mode)
  FLUTTERWAVE_WEBHOOK_HASH the "secret hash" set in the Flutterwave dashboard for webhooks
  FLUTTERWAVE_BASE_URL     defaults to https://api.flutterwave.com/v3
  FLUTTERWAVE_MAX_RETRIES  attempts allowed in one checkout (default 5)
  CHECKOUT_SESSION_MINUTES how long the hosted checkout stays open (default 60, at most 1440)

In the Flutterwave dashboard (Settings > Webhooks) tick "Receive webhook response in JSON format",
"Enable v3 webhooks", "Enable webhook retries" and "Enable resend webhook from the dashboard". The
handler also copes with form-encoded and legacy flat bodies, but JSON v3 is what it is tested on.
"""

import base64
import hashlib
import hmac
import http.client
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from rest_framework.exceptions import APIException

from .billing import ZERO_DECIMAL_CURRENCIES
from .providers import Verification, checkout_closed, return_url

log = logging.getLogger(__name__)
TIMEOUT_SECONDS = 20
PAYMENT_OPTIONS = {"USD": "card", "RWF": "card,mobilemoneyrwanda"}


class ProviderUnavailable(APIException):
    status_code = 503
    default_detail = gettext_lazy("The payment service isn't answering right now. Please try again in a few minutes.")
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
        try:
            body = exc.read().decode(errors="replace")
        except (OSError, http.client.HTTPException):
            body = ""
        if exc.code >= 500 or exc.code in (401, 403, 408, 429):
            # Flutterwave (or our key) is failing, which is not the same as "no such transaction":
            # callers must not act on it, and the webhook must answer 503 so Flutterwave retries.
            log.warning("Flutterwave %s %s failed: %s %s", method, path, exc.code, body[:300])
            raise ProviderUnavailable()
        try:
            return json.loads(body)
        except ValueError:
            log.warning("Flutterwave %s %s failed: %s %s", method, path, exc.code, body[:300])
            raise ProviderUnavailable()
    except (OSError, http.client.HTTPException, ValueError) as exc:
        # Connection refused, reset or dropped mid-answer, TLS errors, timeouts, a garbled body.
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
        customer = {
            "email": user.email or school.email or settings.BILLING_FALLBACK_EMAIL,
            "name": user.display_name,
        }
        if school.phone:
            customer["phonenumber"] = school.phone
        payload = {
            "tx_ref": payment.reference,
            "amount": _amount_text(payment),
            "currency": payment.currency,
            "redirect_url": return_url(payment),
            "payment_options": PAYMENT_OPTIONS.get(payment.currency, "card"),
            "customer": customer,
            # Shown on Flutterwave's page, in the language the administrator uses Iga in.
            "customizations": {
                "title": _("%(app)s school subscription") % {"app": settings.APP_NAME},
                "description": _("%(school)s: %(months)s month(s)") % {"school": school.name, "months": payment.months},
            },
            "meta": {"school_id": school.id, "months": payment.months},
            # A known end to the session, so a failed attempt can be judged final once it is over.
            "session_duration": max(1, min(settings.CHECKOUT_SESSION_MINUTES, 1440)),
            "max_retry_attempt": max(1, settings.FLUTTERWAVE_MAX_RETRIES),
        }
        body = _request("POST", "/payments", payload)
        link = (body.get("data") or {}).get("link") if body.get("status") == "success" else None
        if not link:
            log.warning("Flutterwave refused checkout for %s: %s", payment.reference, body.get("message"))
            raise ProviderUnavailable(body.get("message") or ProviderUnavailable.default_detail)
        return link

    def verify(self, payment, transaction_id=""):
        """Ask Flutterwave whether this payment really went through.

        With a transaction id (from the redirect or the webhook) we look that transaction up, so
        we judge the attempt that was just reported rather than whichever attempt a lookup by
        reference returns. Either way the transaction must carry our reference.
        """
        data = None
        if transaction_id and str(transaction_id).isdigit():
            body = _request("GET", f"/transactions/{transaction_id}/verify")
            found = body.get("data") or {}
            if body.get("status") == "success" and found.get("tx_ref") == payment.reference:
                data = found
            else:
                log.warning("Flutterwave transaction %s is not for %s; checking by reference", transaction_id, payment.reference)
        if data is None:
            query = urllib.parse.urlencode({"tx_ref": payment.reference})
            body = _request("GET", f"/transactions/verify_by_reference?{query}")
            data = body.get("data") or {}
            if body.get("status") != "success" or not data:
                return Verification("pending")
            if str(data.get("status", "")).lower() in ("failed", "cancelled"):
                # The lookup by reference returns one attempt, but a checkout can hold several
                # (a declined card, then a good one). Look for a successful one before judging.
                data = self._successful_attempt(payment) or data
        return self._judge(payment, data)

    def _successful_attempt(self, payment):
        """A successful transaction for our reference among all its attempts, verified by id, or None."""
        query = urllib.parse.urlencode({"tx_ref": payment.reference})
        body = _request("GET", f"/transactions?{query}")
        items = body.get("data") if body.get("status") == "success" else None
        for item in items if isinstance(items, list) else []:
            found_id = str(item.get("id", "")) if isinstance(item, dict) else ""
            if not found_id.isdigit() or item.get("tx_ref") != payment.reference:
                continue
            if str(item.get("status", "")).lower() != "successful":
                continue
            checked = _request("GET", f"/transactions/{found_id}/verify")
            data = checked.get("data") or {}
            if checked.get("status") == "success" and data.get("tx_ref") == payment.reference:
                return data
        return None

    def _judge(self, payment, data):
        found_id = str(data.get("id", ""))
        if data.get("tx_ref") != payment.reference:
            log.error("Flutterwave returned another reference for %s: %s", payment.reference, data.get("tx_ref"))
            return Verification("pending")
        status = str(data.get("status", "")).lower()
        if status == "successful":
            amount = _amount(data.get("amount"))
            if str(data.get("currency", "")).upper() == payment.currency and amount is not None and amount >= payment.amount:
                return Verification("succeeded", found_id, data)
            log.error("Flutterwave amount/currency mismatch for %s: %s", payment.reference, data)
            return Verification("failed", found_id, data)
        if status in ("failed", "cancelled"):
            # The payer may still be retrying on the hosted page with the same reference.
            if checkout_closed(payment):
                return Verification("failed", found_id, data)
            return Verification("pending", found_id, data)
        return Verification("pending", found_id, data)

    @staticmethod
    def webhook_is_authentic(request):
        """Flutterwave signs webhooks with the dashboard's secret hash: v3 sends it as is in the
        `verif-hash` header; v4 sends `flutterwave-signature`, a base64 HMAC-SHA256 of the body
        (some of Flutterwave's examples send the hash itself there, which we also accept)."""
        secret = settings.FLUTTERWAVE_WEBHOOK_HASH.encode()
        if not secret:
            return False
        legacy = request.headers.get("verif-hash")
        if legacy:
            return hmac.compare_digest(legacy.encode(), secret)
        signature = request.headers.get("flutterwave-signature")
        if signature:
            expected = base64.b64encode(hmac.new(secret, request.body, hashlib.sha256).digest())
            given = signature.encode()
            return hmac.compare_digest(given, expected) or hmac.compare_digest(given, secret)
        return False

    @staticmethod
    def parse_webhook(content_type, body):
        """The webhook body as a dict: JSON (the recommended setting) or form-encoded (the default).
        Raises ValueError if it is neither."""
        if "application/x-www-form-urlencoded" in (content_type or ""):
            fields = {key: values[-1] for key, values in urllib.parse.parse_qs(body.decode(errors="replace")).items()}
            data = {key[5:-1]: value for key, value in fields.items() if key.startswith("data[") and key.endswith("]")}
            if isinstance(fields.get("data"), str):
                try:
                    decoded = json.loads(fields["data"])
                except ValueError:
                    decoded = None
                if isinstance(decoded, dict):
                    data.update(decoded)
            if data:
                fields["data"] = data
            return fields
        payload = json.loads(body or b"{}")
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _webhook_data(payload):
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    @classmethod
    def webhook_reference(cls, payload):
        """Our reference: data.tx_ref in v3 webhooks, txRef at the top level in the legacy format."""
        data = cls._webhook_data(payload)
        return str(data.get("tx_ref") or data.get("txRef") or payload.get("tx_ref") or payload.get("txRef") or "")

    @classmethod
    def webhook_transaction_id(cls, payload):
        data = cls._webhook_data(payload)
        return str(data.get("id") or payload.get("id") or "")


def _amount_text(payment):
    """The amount as Flutterwave expects it: whole francs for RWF, two decimals otherwise."""
    if payment.currency in ZERO_DECIMAL_CURRENCIES:
        return str(Decimal(payment.amount).quantize(Decimal("1")))
    return str(Decimal(payment.amount).quantize(Decimal("0.01")))
