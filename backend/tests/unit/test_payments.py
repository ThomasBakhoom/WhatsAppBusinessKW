"""Unit tests for Tap Payments service (mock mode)."""

import pytest
from decimal import Decimal

from app.services.tap_payments import TapPaymentsService


class TestTapPayments:
    @pytest.mark.asyncio
    async def test_create_mock_charge(self):
        tap = TapPaymentsService(secret_key="")
        result = await tap.create_charge(
            amount=Decimal("29.900"),
            currency="KWD",
            payment_method="knet",
            return_url="https://example.com/callback",
            reference_id="test-ref-001",
        )
        assert "charge_id" in result
        assert result["charge_id"].startswith("chg_test_")
        assert result["status"] == "INITIATED"
        assert "payment_url" in result

    @pytest.mark.asyncio
    async def test_retrieve_mock_charge(self):
        tap = TapPaymentsService(secret_key="")
        result = await tap.retrieve_charge("chg_test_abc123")
        assert result["status"] == "CAPTURED"

    @pytest.mark.asyncio
    async def test_create_mock_refund(self):
        tap = TapPaymentsService(secret_key="")
        result = await tap.create_refund("chg_test_abc123", Decimal("10.000"))
        assert result["status"] == "REFUNDED"

    def test_parse_webhook(self):
        tap = TapPaymentsService(secret_key="")
        payload = {
            "id": "chg_live_abc123",
            "status": "CAPTURED",
            "amount": 29.900,
            "currency": "KWD",
            "source": {"payment_method": "KNET"},
            "card": {"last_four": "1234", "brand": "KNET"},
            "reference": {"transaction": "inv-001"},
        }
        parsed = tap.parse_webhook(payload)
        assert parsed["charge_id"] == "chg_live_abc123"
        assert parsed["status"] == "CAPTURED"
        assert parsed["card_last_four"] == "1234"
        assert parsed["reference"] == "inv-001"

    def test_source_mapping(self):
        from app.services.tap_payments import SOURCE_MAP
        assert SOURCE_MAP["knet"] == "src_kw.knet"
        assert SOURCE_MAP["visa"] == "src_card"
        assert SOURCE_MAP["mastercard"] == "src_card"
