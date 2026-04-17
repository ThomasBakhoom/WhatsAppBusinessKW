"""Integration tests for business glossary API.

Covers creating and listing glossary terms with Kuwaiti dialect examples.
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
            "company_name": f"Gls {slug} {unique}",
            "email": f"gls-{slug}-{unique}@example.com",
            "username": f"gls_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Gls",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_glossary_term(client: AsyncClient):
    """POST /v1/glossary should return 201 with a Kuwaiti dialect term."""
    token, _ = await _register(client, "gls_create")
    r = await client.post(
        "/v1/glossary",
        json={
            "term": "\u0686\u0627\u064a \u0643\u0631\u0643",
            "definition": "Kuwaiti karak chai - spiced milk tea popular in Kuwait",
            "aliases": ["karak", "chai karak"],
            "category": "product",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["term"] == "\u0686\u0627\u064a \u0643\u0631\u0643"
    assert body["category"] == "product"
    assert "id" in body


@pytest.mark.asyncio
async def test_list_glossary_terms(client: AsyncClient):
    """GET /v1/glossary should return at least 1 term after creation."""
    token, _ = await _register(client, "gls_list")
    await client.post(
        "/v1/glossary",
        json={
            "term": "\u0645\u0634\u0628\u0648\u0633",
            "definition": "Machboos - traditional Kuwaiti rice dish",
            "aliases": ["machboos", "machbous"],
            "category": "product",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    r = await client.get(
        "/v1/glossary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    terms = {t["term"] for t in items}
    assert "\u0645\u0634\u0628\u0648\u0633" in terms
