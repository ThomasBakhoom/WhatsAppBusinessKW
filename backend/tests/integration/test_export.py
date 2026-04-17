"""Integration tests for data export API.

Covers CSV export for contacts and conversations.
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
            "company_name": f"Exp {slug} {unique}",
            "email": f"exp-{slug}-{unique}@example.com",
            "username": f"exp_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Exp",
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
async def test_export_contacts_csv(client: AsyncClient):
    """GET /v1/export/contacts should return 200 with CSV data."""
    token, _ = await _register(client, "exp_contacts")
    await _create_contact(client, token, "ExportMe")

    r = await client.get(
        "/v1/export/contacts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    # CSV should contain the header row and at least one data row
    lines = r.text.strip().split("\n")
    assert len(lines) >= 2
    assert "phone" in lines[0]
    assert "ExportMe" in r.text


@pytest.mark.asyncio
async def test_export_conversations_csv(client: AsyncClient):
    """GET /v1/export/conversations should return 200 with CSV data."""
    token, _ = await _register(client, "exp_convs")
    contact_id = await _create_contact(client, token, "ConvContact")

    # Start a conversation so there is data to export
    conv_r = await client.post(
        "/v1/conversations",
        json={"contact_id": contact_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert conv_r.status_code == 201, conv_r.text

    r = await client.get(
        "/v1/export/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    lines = r.text.strip().split("\n")
    assert len(lines) >= 2
    assert "contact_id" in lines[0]
