"""Integration tests for the RLS + audit + rate-limit layer.

These tests exercise the app through FastAPI's ASGI stack using the
in-pytest test client (conftest.py). They focus on logic that doesn't
require a separate Postgres with the full migration set — i.e. the API
behaviour that was rewritten in the RLS + audit work:

  * Cross-tenant isolation at the contact API level.
  * Audit log entries written for mutations, including actor fields.
  * Rate-limit response headers.

For true RLS enforcement (PostgreSQL policies under a non-superuser
role) see the end-to-end curl chain in the README / commit log. The
pytest harness creates tables via Base.metadata.create_all and uses the
DATABASE_URL role, which in dev is a superuser — so RLS is bypassed in
this harness by design. The app-layer `company_id` filters still apply,
and THAT's what these tests verify.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(client: AsyncClient, slug: str) -> tuple[str, str]:
    """Register a fresh company. Returns (access_token, company_id).

    We append a uuid fragment so tests can run repeatedly against a live DB
    without colliding on unique(email) / unique(company.slug).
    """
    unique = uuid.uuid4().hex[:8]
    r = await client.post(
        "/v1/auth/register",
        json={
            "company_name": f"RLS {slug} {unique}",
            "email": f"rls-{slug}-{unique}@example.com",
            "username": f"rls_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "RLS",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


def _unique_phone() -> str:
    """Generate a KW-format phone number unique enough for repeated test runs."""
    # 8-digit local number, KW prefix +965
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


# ── Cross-tenant isolation ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tenant_cannot_list_other_tenants_contacts(client: AsyncClient):
    """Each tenant's contact list must only contain its own rows."""
    acme_token, _ = await _register(client, "acme")
    beta_token, _ = await _register(client, "beta")

    await _create_contact(client, acme_token, "AcmeAlpha")
    await _create_contact(client, beta_token, "BetaBravo")

    acme_list = await client.get(
        "/v1/contacts?limit=50", headers={"Authorization": f"Bearer {acme_token}"}
    )
    beta_list = await client.get(
        "/v1/contacts?limit=50", headers={"Authorization": f"Bearer {beta_token}"}
    )
    assert acme_list.status_code == 200
    assert beta_list.status_code == 200

    acme_names = {c["first_name"] for c in acme_list.json()["data"]}
    beta_names = {c["first_name"] for c in beta_list.json()["data"]}
    assert "AcmeAlpha" in acme_names
    assert "AcmeAlpha" not in beta_names
    assert "BetaBravo" in beta_names
    assert "BetaBravo" not in acme_names


@pytest.mark.asyncio
async def test_tenant_cannot_read_other_tenants_contact_by_id(client: AsyncClient):
    """A 404 (not 200) for a cross-tenant GET-by-id proves app-level isolation."""
    acme_token, _ = await _register(client, "acme2")
    beta_token, _ = await _register(client, "beta2")

    beta_cid = await _create_contact(client, beta_token, "BetaCharlie")

    r = await client.get(
        f"/v1/contacts/{beta_cid}",
        headers={"Authorization": f"Bearer {acme_token}"},
    )
    assert r.status_code == 404


# ── Audit entries are written with attribution ────────────────────────────────


@pytest.mark.asyncio
async def test_audit_log_written_for_contact_lifecycle(
    client: AsyncClient,
    db_session_privileged,
):
    token, company_id = await _register(client, "audit_lifecycle")
    cid = await _create_contact(client, token, "AuditLifecycle")
    await client.patch(
        f"/v1/contacts/{cid}",
        json={"first_name": "Renamed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.delete(
        f"/v1/contacts/{cid}",
        headers={"Authorization": f"Bearer {token}"},
    )

    from sqlalchemy import select
    from app.models.audit import AuditLog

    result = await db_session_privileged.execute(
        select(AuditLog.action, AuditLog.description, AuditLog.user_id)
        .where(AuditLog.company_id == company_id)
        .order_by(AuditLog.created_at)
    )
    rows = result.all()

    actions = [r[0] for r in rows]
    assert "company.registered" in actions
    assert "user.registered" in actions
    assert "contact.created" in actions
    assert "contact.updated" in actions
    assert "contact.deleted" in actions

    user_ids = [r[2] for r in rows if r[0] == "contact.updated"]
    assert user_ids and all(uid is not None for uid in user_ids)


@pytest.mark.asyncio
async def test_audit_log_diff_captures_field_changes(
    client: AsyncClient,
    db_session_privileged,
):
    token, company_id = await _register(client, "diff")
    cid = await _create_contact(client, token, "BeforeName")
    await client.patch(
        f"/v1/contacts/{cid}",
        json={"first_name": "AfterName"},
        headers={"Authorization": f"Bearer {token}"},
    )

    from sqlalchemy import select
    from app.models.audit import AuditLog

    result = await db_session_privileged.execute(
        select(AuditLog.changes)
        .where(AuditLog.company_id == company_id, AuditLog.action == "contact.updated")
    )
    changes = result.scalar_one()

    assert changes is not None
    assert changes["first_name"]["old"] == "BeforeName"
    assert changes["first_name"]["new"] == "AfterName"


# ── Rate limiting ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_limit_headers_present_on_v1_responses(client: AsyncClient):
    """Every /v1/* response should include the X-RateLimit-* family."""
    r = await client.post(
        "/v1/auth/login", json={"email": "rl-header@test.local", "password": "x"}
    )
    # 401 for bad creds is fine; we're only checking headers.
    for header in ("x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-window"):
        assert header in {k.lower() for k in r.headers.keys()}, (
            f"missing {header} in {list(r.headers.keys())}"
        )
