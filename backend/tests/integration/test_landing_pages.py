"""Integration tests for landing pages API.

Covers create, public access, and draft-page 404 behaviour.
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
            "company_name": f"Lp {slug} {unique}",
            "email": f"lp-{slug}-{unique}@example.com",
            "username": f"lp_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Lp",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


def _page_payload(title: str = "Promo Page", slug: str | None = None) -> dict:
    """Minimal valid landing page payload."""
    unique = uuid.uuid4().hex[:6]
    return {
        "title": title,
        "slug": slug or f"promo-{unique}",
        "blocks": [
            {"type": "hero", "content": {"heading": "Welcome"}, "settings": {}},
            {"type": "cta", "content": {"label": "Chat now"}, "settings": {}},
        ],
    }


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_landing_page(client: AsyncClient):
    """POST /v1/landing-pages should return 201 with the created page."""
    token, _ = await _register(client, "lp_create")
    payload = _page_payload("My Landing Page")
    r = await client.post(
        "/v1/landing-pages",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "My Landing Page"
    assert body["status"] == "draft"
    assert len(body["blocks"]) == 2
    assert "id" in body


@pytest.mark.asyncio
async def test_public_page_access(client: AsyncClient):
    """Create + publish a page, then fetch via public slug WITHOUT auth."""
    token, _ = await _register(client, "lp_public")
    slug = f"public-{uuid.uuid4().hex[:6]}"
    payload = _page_payload("Public Page", slug=slug)

    # Create
    cr = await client.post(
        "/v1/landing-pages",
        json=payload,
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

    # Public fetch (no auth header)
    r = await client.get(f"/v1/landing-pages/public/{slug}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == slug
    assert body["status"] == "published"


@pytest.mark.asyncio
async def test_public_page_404_unpublished(client: AsyncClient):
    """Draft page must NOT be accessible via public slug."""
    token, _ = await _register(client, "lp_draft")
    slug = f"draft-{uuid.uuid4().hex[:6]}"
    payload = _page_payload("Draft Only", slug=slug)

    cr = await client.post(
        "/v1/landing-pages",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cr.status_code == 201, cr.text

    # Public fetch should 404
    r = await client.get(f"/v1/landing-pages/public/{slug}")
    assert r.status_code == 404, r.text
