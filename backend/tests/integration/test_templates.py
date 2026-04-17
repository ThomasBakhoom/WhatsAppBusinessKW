"""Integration tests for message templates API.

Template sync from Meta is skipped because it requires the WhatsApp Cloud API.
Follows the same patterns as test_rls_and_audit.py.
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
            "company_name": f"Tpl {slug} {unique}",
            "email": f"tpl-{slug}-{unique}@example.com",
            "username": f"tpl_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Tpl",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


def _template_payload(name: str = "order_confirmation") -> dict:
    """Minimal valid template payload."""
    return {
        "name": name,
        "language": "en",
        "category": "UTILITY",
        "body": "Your order {{1}} has been confirmed. Thank you!",
    }


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_template(client: AsyncClient):
    """POST /v1/templates should return 201 with the created template."""
    token, _ = await _register(client, "tpl_create")
    r = await client.post(
        "/v1/templates",
        json=_template_payload("welcome_msg"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "welcome_msg"
    assert body["category"] == "UTILITY"
    assert body["language"] == "en"
    assert "id" in body


@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient):
    """GET /v1/templates should return a list containing the created template."""
    token, _ = await _register(client, "tpl_list")
    await client.post(
        "/v1/templates",
        json=_template_payload("promo_blast"),
        headers={"Authorization": f"Bearer {token}"},
    )

    r = await client.get(
        "/v1/templates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    names = {t["name"] for t in items}
    assert "promo_blast" in names
