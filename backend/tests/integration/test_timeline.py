"""Integration tests for the contact timeline API.

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
            "company_name": f"TL {slug} {unique}",
            "email": f"tl-{slug}-{unique}@example.com",
            "username": f"tl_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "TL",
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


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contact_timeline(client: AsyncClient):
    """GET /v1/timeline/{contact_id} should return events for the contact."""
    token, _ = await _register(client, "timeline")
    contact_id = await _create_contact(client, token, "TimelineContact")

    # Start a conversation with an initial message to populate the timeline
    conv_r = await client.post(
        "/v1/conversations",
        json={"contact_id": contact_id, "message": "Hello from test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert conv_r.status_code == 201, conv_r.text

    r = await client.get(
        f"/v1/timeline/{contact_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["contact_id"] == contact_id
    assert "events" in body
    # Should have at least a conversation event
    assert len(body["events"]) >= 1
    event_types = {e["type"] for e in body["events"]}
    assert "conversation" in event_types
