"""Tap Payments service - K-Net, Visa, Mastercard integration for Kuwait."""

import hashlib
import hmac
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

TAP_API_URL = "https://api.tap.company/v2"

# Tap source IDs for Kuwait payment methods
SOURCE_MAP = {
    "knet": "src_kw.knet",
    "visa": "src_card",
    "mastercard": "src_card",
    "apple_pay": "src_apple_pay",
}


class TapPaymentsService:
    """Tap Payments API wrapper for Kuwait market."""

    def __init__(self, secret_key: str | None = None):
        self.secret_key = secret_key or settings.tap_secret_key
        self._client = httpx.AsyncClient(
            base_url=TAP_API_URL,
            headers={
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def create_charge(
        self,
        *,
        amount: Decimal,
        currency: str = "KWD",
        payment_method: str = "knet",
        customer_email: str | None = None,
        customer_name: str | None = None,
        customer_phone: str | None = None,
        description: str = "Subscription Payment",
        reference_id: str = "",
        return_url: str,
        post_url: str | None = None,
    ) -> dict[str, Any]:
        """Create a Tap Payments charge. Returns charge ID and redirect URL."""
        source_id = SOURCE_MAP.get(payment_method, "src_card")

        payload: dict[str, Any] = {
            "amount": float(amount),
            "currency": currency,
            "threeDSecure": True,
            "save_card": False,
            "description": description,
            "reference": {"transaction": reference_id},
            "receipt": {"email": customer_email is not None, "sms": customer_phone is not None},
            "source": {"id": source_id},
            "redirect": {"url": return_url},
        }

        if post_url:
            payload["post"] = {"url": post_url}

        if customer_email or customer_name or customer_phone:
            customer: dict[str, Any] = {}
            if customer_email:
                customer["email"] = customer_email
            if customer_phone:
                customer["phone"] = {"country_code": "965", "number": customer_phone}
            if customer_name:
                parts = customer_name.split(" ", 1)
                customer["first_name"] = parts[0]
                if len(parts) > 1:
                    customer["last_name"] = parts[1]
            payload["customer"] = customer

        if not self.secret_key:
            # Return mock charge for development
            return self._mock_charge(reference_id, amount, currency)

        response = await self._client.post("/charges", json=payload)
        response.raise_for_status()
        data = response.json()

        logger.info(
            "tap_charge_created",
            charge_id=data.get("id"),
            amount=float(amount),
            currency=currency,
            payment_method=payment_method,
        )

        return {
            "charge_id": data["id"],
            "status": data["status"],
            "payment_url": data.get("transaction", {}).get("url", ""),
            "gateway_response": data,
        }

    async def retrieve_charge(self, charge_id: str) -> dict[str, Any]:
        """Retrieve charge details from Tap."""
        if not self.secret_key:
            return self._mock_charge_status(charge_id)

        response = await self._client.get(f"/charges/{charge_id}")
        response.raise_for_status()
        return response.json()

    async def create_refund(
        self, charge_id: str, amount: Decimal, reason: str = ""
    ) -> dict[str, Any]:
        """Create a refund for a charge."""
        if not self.secret_key:
            return {"id": f"refund_mock_{charge_id}", "status": "REFUNDED"}

        response = await self._client.post("/refunds", json={
            "charge_id": charge_id,
            "amount": float(amount),
            "currency": "KWD",
            "reason": reason,
        })
        response.raise_for_status()
        return response.json()

    @staticmethod
    def verify_webhook_signature(
        raw_body: bytes,
        signature_header: str | None,
        webhook_secret: str | None = None,
    ) -> bool:
        """
        Verify a Tap webhook HMAC signature.

        Tap signs webhook bodies with HMAC-SHA256 using the merchant's webhook
        secret. The signature is delivered in the `hashstring` header.

        Returns False if:
          - No secret is configured (prod should always configure one)
          - No signature header is present
          - The signature does not match

        We use `hmac.compare_digest` to avoid timing attacks.
        """
        secret = webhook_secret if webhook_secret is not None else settings.tap_webhook_secret
        if not secret:
            logger.error("tap_webhook_secret_missing")
            return False
        if not signature_header:
            logger.warning("tap_webhook_signature_missing")
            return False

        expected = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        # Tap may send the signature as plain hex or prefixed (`sha256=<hex>`);
        # normalise both sides before comparing.
        provided = signature_header.strip()
        if provided.lower().startswith("sha256="):
            provided = provided[len("sha256="):]

        match = hmac.compare_digest(expected, provided)
        if not match:
            logger.warning(
                "tap_webhook_signature_mismatch",
                provided_prefix=provided[:8] if provided else None,
            )
        return match

    def parse_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Parse a Tap webhook payload."""
        return {
            "charge_id": payload.get("id", ""),
            "status": payload.get("status", ""),
            "amount": payload.get("amount", 0),
            "currency": payload.get("currency", "KWD"),
            "payment_method": payload.get("source", {}).get("payment_method", ""),
            "card_last_four": payload.get("card", {}).get("last_four", ""),
            "card_brand": payload.get("card", {}).get("brand", ""),
            "reference": payload.get("reference", {}).get("transaction", ""),
            "gateway_response": payload,
        }

    async def close(self):
        await self._client.aclose()

    def _mock_charge(self, ref: str, amount: Decimal, currency: str) -> dict[str, Any]:
        """Mock charge for dev/test without Tap API key."""
        import uuid
        charge_id = f"chg_test_{uuid.uuid4().hex[:12]}"
        return {
            "charge_id": charge_id,
            "status": "INITIATED",
            "payment_url": f"https://tap.company/mock-payment/{charge_id}",
            "gateway_response": {
                "id": charge_id,
                "status": "INITIATED",
                "amount": float(amount),
                "currency": currency,
                "reference": {"transaction": ref},
            },
        }

    def _mock_charge_status(self, charge_id: str) -> dict[str, Any]:
        return {
            "id": charge_id,
            "status": "CAPTURED",
            "amount": 0,
            "currency": "KWD",
            "source": {"payment_method": "KNET"},
            "card": {"last_four": "1234", "brand": "KNET"},
            "reference": {"transaction": ""},
        }
