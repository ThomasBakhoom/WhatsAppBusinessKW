"""Integration tests for the payments / subscription API.

Plans are global (no company_id), so we seed them via db_session_privileged.
Subscription and cancel flows go through the real ASGI stack.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Plan


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(client: AsyncClient, slug: str) -> tuple[str, str]:
    """Register a fresh company.  Returns (access_token, company_id)."""
    unique = uuid.uuid4().hex[:8]
    r = await client.post(
        "/v1/auth/register",
        json={
            "company_name": f"Pay {slug} {unique}",
            "email": f"pay-{slug}-{unique}@example.com",
            "username": f"pay_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Pay",
            "last_name": slug.title(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["tokens"]["access_token"], body["user"]["company_id"]


async def _seed_plan(db: AsyncSession, suffix: str) -> str:
    """Insert a Plan row directly and return its id (str)."""
    unique = uuid.uuid4().hex[:8]
    plan = Plan(
        name=f"test-{suffix}-{unique}",
        display_name=f"Test Plan {suffix.title()}",
        price_monthly=Decimal("9.900"),
        price_yearly=Decimal("99.000"),
        currency="KWD",
        max_contacts=1000,
        max_conversations_per_month=5000,
        max_team_members=5,
        max_automations=10,
        max_pipelines=3,
        max_landing_pages=5,
        has_ai_features=False,
        has_api_access=False,
        has_whatsapp_templates=True,
        is_active=True,
        sort_order=1,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return str(plan.id)


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_plans_empty(client: AsyncClient):
    """GET /payments/plans should return a list (possibly empty or populated)."""
    token, _ = await _register(client, "plans_list")
    r = await client.get(
        "/v1/payments/plans",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_create_subscription(client: AsyncClient, db_session_privileged: AsyncSession):
    """POST /payments/subscription should create an active subscription."""
    token, _ = await _register(client, "sub_create")
    plan_id = await _seed_plan(db_session_privileged, "sub")

    r = await client.post(
        "/v1/payments/subscription",
        json={"plan_id": plan_id, "billing_cycle": "monthly"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    sub = r.json()
    assert sub["status"] == "active"
    assert sub["plan_id"] == plan_id
    assert sub["billing_cycle"] == "monthly"


@pytest.mark.asyncio
async def test_cancel_subscription(client: AsyncClient, db_session_privileged: AsyncSession):
    """POST /payments/subscription/cancel should mark cancel_at_period_end."""
    token, _ = await _register(client, "sub_cancel")
    plan_id = await _seed_plan(db_session_privileged, "cancel")

    # Create subscription first
    create_r = await client.post(
        "/v1/payments/subscription",
        json={"plan_id": plan_id, "billing_cycle": "monthly"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_r.status_code == 201

    # Cancel at period end
    cancel_r = await client.post(
        "/v1/payments/subscription/cancel",
        json={"cancel_at_period_end": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cancel_r.status_code == 200, cancel_r.text
    body = cancel_r.json()
    assert body["cancel_at_period_end"] is True
    assert body["cancelled_at"] is not None
