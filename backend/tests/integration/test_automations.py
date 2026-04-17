"""Integration tests for automations API.

Covers automation CRUD and toggle. Follows the same patterns as
test_rls_and_audit.py -- each test registers a fresh tenant.
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
            "company_name": f"Auto {slug} {unique}",
            "email": f"auto-{slug}-{unique}@example.com",
            "username": f"auto_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Auto",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


def _automation_payload(name: str = "Welcome Bot") -> dict:
    """Minimal valid automation payload."""
    return {
        "name": name,
        "trigger_event": "message.received",
        "conditions": [
            {"field": "message.content", "operator": "contains", "value": "hello"}
        ],
        "actions": [
            {
                "action_type": "auto_reply",
                "config": {"message": "Hi there!"},
                "sort_order": 0,
            }
        ],
        "is_active": True,
    }


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_automation(client: AsyncClient):
    """POST /v1/automations should return 201 with the created automation."""
    token, _ = await _register(client, "auto_create")
    r = await client.post(
        "/v1/automations",
        json=_automation_payload("New Auto"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "New Auto"
    assert body["trigger_event"] == "message.received"
    assert body["is_active"] is True
    assert "id" in body


@pytest.mark.asyncio
async def test_list_automations(client: AsyncClient):
    """GET /v1/automations should return a list containing the created automation."""
    token, _ = await _register(client, "auto_list")
    await client.post(
        "/v1/automations",
        json=_automation_payload("Listable"),
        headers={"Authorization": f"Bearer {token}"},
    )

    r = await client.get(
        "/v1/automations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    names = {a["name"] for a in items}
    assert "Listable" in names


@pytest.mark.asyncio
async def test_toggle_automation(client: AsyncClient):
    """POST /v1/automations/{id}/toggle should flip is_active."""
    token, _ = await _register(client, "auto_toggle")
    create_r = await client.post(
        "/v1/automations",
        json=_automation_payload("Toggle Me"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_r.status_code == 201
    auto_id = create_r.json()["id"]
    assert create_r.json()["is_active"] is True

    toggle_r = await client.post(
        f"/v1/automations/{auto_id}/toggle",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert toggle_r.status_code == 200, toggle_r.text
    assert toggle_r.json()["is_active"] is False
