"""Integration tests for the shipping API.

Covers provider creation, shipment creation with a valid contact and provider,
and shipment listing. Follows the same patterns as test_rls_and_audit.py.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(client: AsyncClient, slug: str) -> tuple[str, str]:
    """Register a fresh company.  Returns (access_token, company_id)."""
    unique = uuid.uuid4().hex[:8]
    r = await client.post(
        "/v1/auth/register",
        json={
            "company_name": f"Ship {slug} {unique}",
            "email": f"ship-{slug}-{unique}@example.com",
            "username": f"ship_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Ship",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


def _unique_phone() -> str:
    n = uuid.uuid4().int % 100000000
    return f"+965{n:08d}"


async def _create_contact(client: AsyncClient, token: str, name: str) -> str:
    r = await client.post(
        "/v1/contacts",
        json={"phone": _unique_phone(), "first_name": name, "last_name": "X"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_provider(client: AsyncClient, token: str) -> str:
    """Create a shipping provider and return its id."""
    unique = uuid.uuid4().hex[:6]
    r = await client.post(
        "/v1/shipping/providers",
        json={
            "carrier": "aramex",
            "display_name": f"Aramex {unique}",
            "is_default": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _address() -> dict:
    return {
        "line1": "Block 5, Street 10",
        "city": "Kuwait City",
        "country": "KW",
    }


async def _create_shipment(client: AsyncClient, token: str, provider_id: str, contact_id: str) -> dict:
    """Create a shipment and return the full response body."""
    r = await client.post(
        "/v1/shipping",
        json={
            "provider_id": provider_id,
            "carrier": "aramex",
            "contact_id": contact_id,
            "recipient_name": "Test Recipient",
            "recipient_phone": _unique_phone(),
            "origin_address": _address(),
            "destination_address": _address(),
            "weight_kg": 2.5,
            "description": "Test parcel",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_shipping_provider(client: AsyncClient):
    """POST /shipping/providers should return the new provider."""
    token, _ = await _register(client, "prov_create")
    unique = uuid.uuid4().hex[:6]

    r = await client.post(
        "/v1/shipping/providers",
        json={
            "carrier": "dhl",
            "display_name": f"DHL {unique}",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["carrier"] == "dhl"
    assert body["display_name"] == f"DHL {unique}"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_create_shipment(client: AsyncClient):
    """POST /shipping should create a shipment with tracking info placeholder."""
    token, _ = await _register(client, "ship_create")
    provider_id = await _create_provider(client, token)
    contact_id = await _create_contact(client, token, "ShipContact")

    body = await _create_shipment(client, token, provider_id, contact_id)
    assert body["carrier"] == "aramex"
    assert body["contact_id"] == contact_id
    assert body["status"] == "created"
    assert body["recipient_name"] == "Test Recipient"


@pytest.mark.asyncio
async def test_list_shipments(client: AsyncClient):
    """GET /shipping should list shipments with correct count."""
    token, _ = await _register(client, "ship_list")
    provider_id = await _create_provider(client, token)
    contact_id = await _create_contact(client, token, "ListContact")

    await _create_shipment(client, token, provider_id, contact_id)
    await _create_shipment(client, token, provider_id, contact_id)

    r = await client.get(
        "/v1/shipping?limit=50",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["meta"]["total"] == 2
    assert len(body["data"]) == 2
