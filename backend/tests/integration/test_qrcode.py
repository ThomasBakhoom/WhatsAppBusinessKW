"""Integration test for QR code generation API.

Covers WhatsApp QR code generation endpoint.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


# -- Helpers -----------------------------------------------------------------


async def _register(client: AsyncClient, slug: str) -> tuple[str, str]:
    """Register a fresh company. Returns (access_token, company_id)."""
    unique = uuid.uuid4().hex[:8]
    r = await client.post(
        "/v1/auth/register",
        json={
            "company_name": f"Qr {slug} {unique}",
            "email": f"qr-{slug}-{unique}@example.com",
            "username": f"qr_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Qr",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_qr_code(client: AsyncClient):
    """GET /v1/qr/whatsapp should return 200 with image or QR URL."""
    token, _ = await _register(client, "qr_gen")
    r = await client.get(
        "/v1/qr/whatsapp",
        params={"phone": "+96512345678", "message": "Hello from test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    # Response is either PNG image or JSON with qr_url
    if r.headers.get("content-type", "").startswith("image/png"):
        assert len(r.content) > 100  # non-trivial PNG data
    else:
        body = r.json()
        assert "qr_url" in body or "whatsapp_url" in body
