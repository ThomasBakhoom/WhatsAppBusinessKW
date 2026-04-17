"""Integration tests for user management API.

Covers list team members, invite user, and update user status.
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
            "company_name": f"Usr {slug} {unique}",
            "email": f"usr-{slug}-{unique}@example.com",
            "username": f"usr_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Usr",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_team_members(client: AsyncClient):
    """GET /v1/users should return at least the owner."""
    token, _ = await _register(client, "usr_list")
    r = await client.get(
        "/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    users = r.json()
    assert isinstance(users, list)
    assert len(users) >= 1


@pytest.mark.asyncio
async def test_invite_user(client: AsyncClient):
    """POST /v1/users/invite should create a new team member."""
    token, _ = await _register(client, "usr_invite")
    unique = uuid.uuid4().hex[:8]
    r = await client.post(
        "/v1/users/invite",
        json={
            "email": f"invited-{unique}@example.com",
            "first_name": "Invited",
            "last_name": "User",
            "role": "agent",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == f"invited-{unique}@example.com"
    assert "id" in body


@pytest.mark.asyncio
async def test_update_user_status(client: AsyncClient):
    """PATCH /v1/users/{id} should toggle user active status."""
    token, _ = await _register(client, "usr_patch")
    unique = uuid.uuid4().hex[:8]

    # Invite a user first
    inv = await client.post(
        "/v1/users/invite",
        json={
            "email": f"toggle-{unique}@example.com",
            "first_name": "Toggle",
            "last_name": "User",
            "role": "agent",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert inv.status_code == 201, inv.text
    user_id = inv.json()["id"]

    # Deactivate
    r = await client.patch(
        f"/v1/users/{user_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "User updated"
