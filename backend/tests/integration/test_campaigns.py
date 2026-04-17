"""Integration tests for campaigns API.

Covers campaign CRUD. The send endpoint is skipped because it requires
the WhatsApp Cloud API. Follows the same patterns as test_rls_and_audit.py.
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
            "company_name": f"Camp {slug} {unique}",
            "email": f"camp-{slug}-{unique}@example.com",
            "username": f"camp_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Camp",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


def _campaign_payload(name: str = "Spring Sale") -> dict:
    """Minimal valid campaign payload."""
    return {
        "name": name,
        "message_type": "template",
        "template_name": "spring_promo",
        "template_language": "en",
        "audience_type": "all",
        "audience_filter": {},
    }


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_campaign(client: AsyncClient):
    """POST /v1/campaigns should return 201 with the created campaign."""
    token, _ = await _register(client, "camp_create")
    r = await client.post(
        "/v1/campaigns",
        json=_campaign_payload("New Campaign"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "New Campaign"
    assert body["status"] == "draft"
    assert "id" in body


@pytest.mark.asyncio
async def test_list_campaigns(client: AsyncClient):
    """GET /v1/campaigns should return a paginated list with count >= 1."""
    token, _ = await _register(client, "camp_list")
    await client.post(
        "/v1/campaigns",
        json=_campaign_payload("Listable Campaign"),
        headers={"Authorization": f"Bearer {token}"},
    )

    r = await client.get(
        "/v1/campaigns",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["total"] >= 1
    names = {c["name"] for c in body["data"]}
    assert "Listable Campaign" in names


@pytest.mark.asyncio
async def test_get_campaign_detail(client: AsyncClient):
    """GET /v1/campaigns/{id} should return the full campaign record."""
    token, _ = await _register(client, "camp_detail")
    create_r = await client.post(
        "/v1/campaigns",
        json=_campaign_payload("Detail Campaign"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_r.status_code == 201
    camp_id = create_r.json()["id"]

    r = await client.get(
        f"/v1/campaigns/{camp_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == camp_id
    assert body["name"] == "Detail Campaign"
    assert "status" in body
    assert "total_recipients" in body
    assert "created_at" in body
