"""Integration tests for conversations API.

Covers assignment auditing, close-and-reopen semantics, and cross-tenant
isolation for conversations. Complements the existing unit tests in
tests/unit/test_conversations.py.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(client: AsyncClient, slug: str) -> tuple[str, str, str]:
    """Register a fresh company.  Returns (access_token, company_id, user_id)."""
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
    return body["tokens"]["access_token"], body["user"]["company_id"], body["user"]["id"]


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


async def _start_conversation(client: AsyncClient, token: str, contact_id: str) -> str:
    """Start a conversation and return its id."""
    r = await client.post(
        "/v1/conversations",
        json={"contact_id": contact_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_conversation_assignment(
    client: AsyncClient,
    db_session_privileged: AsyncSession,
):
    """Assigning a conversation should produce a conversation.assigned audit entry."""
    token, company_id, user_id = await _register(client, "assign")
    contact_id = await _create_contact(client, token, "AssignContact")
    conv_id = await _start_conversation(client, token, contact_id)

    # Assign the conversation to the same user
    r = await client.patch(
        f"/v1/conversations/{conv_id}",
        json={"assigned_to_user_id": user_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["assigned_to_user_id"] == user_id

    # Check audit log for conversation.assigned
    from sqlalchemy import select
    from app.models.audit import AuditLog

    result = await db_session_privileged.execute(
        select(AuditLog.action)
        .where(
            AuditLog.company_id == company_id,
            AuditLog.action == "conversation.assigned",
        )
    )
    rows = result.all()
    assert len(rows) >= 1, "Expected at least one conversation.assigned audit entry"


@pytest.mark.asyncio
async def test_conversation_close_and_reopen(client: AsyncClient):
    """Closing a conversation and starting a new one for the same contact
    should create a brand-new conversation row."""
    token, _, _ = await _register(client, "reopen")
    contact_id = await _create_contact(client, token, "ReopenContact")

    conv1_id = await _start_conversation(client, token, contact_id)

    # Close the conversation
    close_r = await client.patch(
        f"/v1/conversations/{conv1_id}",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert close_r.status_code == 200
    assert close_r.json()["status"] == "closed"

    # Start a new conversation with the same contact
    r = await client.post(
        "/v1/conversations",
        json={"contact_id": contact_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    conv2_id = r.json()["id"]

    # Must be a new conversation, not the closed one
    assert conv2_id != conv1_id


@pytest.mark.asyncio
async def test_cross_tenant_conversation_isolation(client: AsyncClient):
    """Two tenants should never see each other's conversations."""
    token_a, _, _ = await _register(client, "iso_a")
    token_b, _, _ = await _register(client, "iso_b")

    contact_a = await _create_contact(client, token_a, "TenantAContact")
    contact_b = await _create_contact(client, token_b, "TenantBContact")

    conv_a = await _start_conversation(client, token_a, contact_a)
    conv_b = await _start_conversation(client, token_b, contact_b)

    # List as tenant A
    list_a = await client.get(
        "/v1/conversations?limit=50",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert list_a.status_code == 200
    ids_a = {c["id"] for c in list_a.json()["data"]}
    assert conv_a in ids_a
    assert conv_b not in ids_a

    # List as tenant B
    list_b = await client.get(
        "/v1/conversations?limit=50",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert list_b.status_code == 200
    ids_b = {c["id"] for c in list_b.json()["data"]}
    assert conv_b in ids_b
    assert conv_a not in ids_b

    # Cross-tenant GET by id should 404
    cross_r = await client.get(
        f"/v1/conversations/{conv_b}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert cross_r.status_code == 404
