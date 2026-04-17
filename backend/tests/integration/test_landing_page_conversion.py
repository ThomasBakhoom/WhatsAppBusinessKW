"""Integration test for landing page conversion tracking.

Covers the public conversion endpoint.
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
            "company_name": f"Conv {slug} {unique}",
            "email": f"conv-{slug}-{unique}@example.com",
            "username": f"conv_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Conv",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_conversion(client: AsyncClient):
    """POST /v1/landing-pages/public/{slug}/convert should return 200 without auth."""
    token, _ = await _register(client, "conv_rec")
    slug = f"convert-{uuid.uuid4().hex[:6]}"

    # Create page
    cr = await client.post(
        "/v1/landing-pages",
        json={
            "title": "Conversion Page",
            "slug": slug,
            "blocks": [{"type": "cta", "content": {"label": "WhatsApp"}, "settings": {}}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cr.status_code == 201, cr.text
    page_id = cr.json()["id"]

    # Publish
    pr = await client.post(
        f"/v1/landing-pages/{page_id}/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pr.status_code == 200, pr.text

    # Record conversion (no auth header)
    r = await client.post(f"/v1/landing-pages/public/{slug}/convert")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"
