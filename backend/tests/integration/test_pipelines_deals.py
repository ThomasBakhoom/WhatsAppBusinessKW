"""Integration tests for pipelines and deals API.

Covers pipeline CRUD, deal lifecycle (create, update, move, soft-delete),
and the Kanban board endpoint. Follows the same patterns as
test_rls_and_audit.py — each test registers a fresh tenant.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(client: AsyncClient, slug: str) -> tuple[str, str, str]:
    """Register a fresh company.  Returns (access_token, company_id, user_id)."""
    unique = uuid.uuid4().hex[:8]
    r = await client.post(
        "/v1/auth/register",
        json={
            "company_name": f"Pipe {slug} {unique}",
            "email": f"pipe-{slug}-{unique}@example.com",
            "username": f"pipe_{slug}_{unique}",
            "password": "securepass123",
            "first_name": "Pipe",
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


async def _create_pipeline_with_stages(
    client: AsyncClient, token: str, name: str = "Sales"
) -> dict:
    """Create a pipeline with two stages and return the full response body."""
    r = await client.post(
        "/v1/pipelines",
        json={
            "name": name,
            "stages": [
                {"name": "Lead", "color": "#6366f1", "sort_order": 0},
                {"name": "Qualified", "color": "#f97316", "sort_order": 1},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_pipeline_with_stages(client: AsyncClient):
    """Creating a pipeline with inline stages should return both stages."""
    token, _, _ = await _register(client, "pstages")
    body = await _create_pipeline_with_stages(client, token, "My Pipeline")

    assert body["name"] == "My Pipeline"
    assert len(body["stages"]) == 2
    stage_names = {s["name"] for s in body["stages"]}
    assert stage_names == {"Lead", "Qualified"}


@pytest.mark.asyncio
async def test_create_deal(client: AsyncClient):
    """A deal created inside a pipeline should be placed in the given stage."""
    token, _, _ = await _register(client, "deal_create")
    pipeline = await _create_pipeline_with_stages(client, token)
    contact_id = await _create_contact(client, token, "DealContact")
    stage_id = pipeline["stages"][0]["id"]

    r = await client.post(
        "/v1/pipelines/deals",
        json={
            "pipeline_id": pipeline["id"],
            "stage_id": stage_id,
            "title": "Enterprise License",
            "value": 15000,
            "contact_id": contact_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    deal = r.json()
    assert deal["pipeline_id"] == pipeline["id"]
    assert deal["stage_id"] == stage_id
    assert deal["title"] == "Enterprise License"
    assert deal["contact_id"] == contact_id


@pytest.mark.asyncio
async def test_update_deal_value(client: AsyncClient):
    """Updating a deal's value should reflect in the response."""
    token, _, _ = await _register(client, "deal_val")
    pipeline = await _create_pipeline_with_stages(client, token)
    stage_id = pipeline["stages"][0]["id"]

    create_r = await client.post(
        "/v1/pipelines/deals",
        json={
            "pipeline_id": pipeline["id"],
            "stage_id": stage_id,
            "title": "Starter Plan",
            "value": 1000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_r.status_code == 201
    deal_id = create_r.json()["id"]

    update_r = await client.patch(
        f"/v1/pipelines/deals/{deal_id}",
        json={"value": 2500},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_r.status_code == 200, update_r.text
    assert float(update_r.json()["value"]) == 2500.0


@pytest.mark.asyncio
async def test_move_deal_between_stages(client: AsyncClient):
    """POST /deals/{id}/move should change the deal's stage."""
    token, _, _ = await _register(client, "deal_move")
    pipeline = await _create_pipeline_with_stages(client, token)
    stages = pipeline["stages"]
    first_stage = stages[0]["id"]
    second_stage = stages[1]["id"]

    create_r = await client.post(
        "/v1/pipelines/deals",
        json={
            "pipeline_id": pipeline["id"],
            "stage_id": first_stage,
            "title": "Moveable Deal",
            "value": 500,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    deal_id = create_r.json()["id"]

    move_r = await client.post(
        f"/v1/pipelines/deals/{deal_id}/move",
        json={"stage_id": second_stage, "position": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert move_r.status_code == 200, move_r.text
    assert move_r.json()["stage_id"] == second_stage


@pytest.mark.asyncio
async def test_delete_deal_soft(client: AsyncClient):
    """Deleting a deal should make it disappear from a subsequent GET."""
    token, _, _ = await _register(client, "deal_del")
    pipeline = await _create_pipeline_with_stages(client, token)

    create_r = await client.post(
        "/v1/pipelines/deals",
        json={
            "pipeline_id": pipeline["id"],
            "stage_id": pipeline["stages"][0]["id"],
            "title": "Ephemeral",
            "value": 100,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    deal_id = create_r.json()["id"]

    del_r = await client.delete(
        f"/v1/pipelines/deals/{deal_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_r.status_code == 200, del_r.text

    get_r = await client.get(
        f"/v1/pipelines/deals/{deal_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_r.status_code == 404


@pytest.mark.asyncio
async def test_kanban_board(client: AsyncClient):
    """GET /{pipeline_id}/board should return columns matching the stages."""
    token, _, _ = await _register(client, "kanban")
    pipeline = await _create_pipeline_with_stages(client, token)
    stages = pipeline["stages"]

    # Create two deals in the first stage
    for title in ("K-Deal1", "K-Deal2"):
        r = await client.post(
            "/v1/pipelines/deals",
            json={
                "pipeline_id": pipeline["id"],
                "stage_id": stages[0]["id"],
                "title": title,
                "value": 1000,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201

    board_r = await client.get(
        f"/v1/pipelines/{pipeline['id']}/board",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert board_r.status_code == 200, board_r.text
    board = board_r.json()

    assert "columns" in board
    assert len(board["columns"]) == 2  # two stages

    # First column should have the 2 deals
    col0 = board["columns"][0]
    assert col0["deal_count"] == 2
    assert len(col0["deals"]) == 2
