"""Unit tests for pipeline and deals."""

import pytest
from httpx import AsyncClient


async def setup_pipeline(client: AsyncClient, suffix: str):
    reg = await client.post("/v1/auth/register", json={
        "email": f"pipe{suffix}@test.kw", "username": f"pipe{suffix}",
        "password": "TestPass123!", "company_name": f"Pipe{suffix} Co",
        "first_name": "P", "last_name": "L",
    })
    token = reg.json()["tokens"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    pipeline = await client.post("/v1/pipelines", json={
        "name": "Test Pipeline",
        "stages": [
            {"name": "New", "color": "#6366f1", "sort_order": 0},
            {"name": "Won", "color": "#22c55e", "sort_order": 1, "is_won": True},
        ],
    }, headers=h)
    return token, h, pipeline.json()


@pytest.mark.asyncio
class TestPipeline:
    async def test_create_pipeline(self, client: AsyncClient):
        _, h, pipeline = await setup_pipeline(client, "p1")
        assert pipeline["name"] == "Test Pipeline"
        assert len(pipeline["stages"]) == 2

    async def test_create_deal(self, client: AsyncClient):
        _, h, pipeline = await setup_pipeline(client, "p2")
        pid = pipeline["id"]
        sid = pipeline["stages"][0]["id"]
        deal = await client.post("/v1/pipelines/deals", json={
            "pipeline_id": pid, "stage_id": sid, "title": "Big Deal", "value": 5000.500,
        }, headers=h)
        assert deal.status_code == 201
        assert deal.json()["title"] == "Big Deal"
        assert float(deal.json()["value"]) == 5000.5

    async def test_kanban_board(self, client: AsyncClient):
        _, h, pipeline = await setup_pipeline(client, "p3")
        pid = pipeline["id"]
        sid = pipeline["stages"][0]["id"]
        await client.post("/v1/pipelines/deals", json={
            "pipeline_id": pid, "stage_id": sid, "title": "Deal A", "value": 1000,
        }, headers=h)
        board = await client.get(f"/v1/pipelines/{pid}/board", headers=h)
        assert board.status_code == 200
        assert len(board.json()["columns"]) == 2
        assert board.json()["columns"][0]["deal_count"] == 1

    async def test_move_deal(self, client: AsyncClient):
        _, h, pipeline = await setup_pipeline(client, "p4")
        pid = pipeline["id"]
        stage1 = pipeline["stages"][0]["id"]
        stage2 = pipeline["stages"][1]["id"]
        deal = await client.post("/v1/pipelines/deals", json={
            "pipeline_id": pid, "stage_id": stage1, "title": "Move Me", "value": 2000,
        }, headers=h)
        did = deal.json()["id"]
        moved = await client.post(f"/v1/pipelines/deals/{did}/move", json={
            "stage_id": stage2, "position": 0,
        }, headers=h)
        assert moved.status_code == 200

    async def test_deal_activities(self, client: AsyncClient):
        _, h, pipeline = await setup_pipeline(client, "p5")
        pid = pipeline["id"]
        sid = pipeline["stages"][0]["id"]
        deal = await client.post("/v1/pipelines/deals", json={
            "pipeline_id": pid, "stage_id": sid, "title": "Activity Test", "value": 100,
        }, headers=h)
        did = deal.json()["id"]
        activities = await client.get(f"/v1/pipelines/deals/{did}/activities", headers=h)
        assert activities.status_code == 200
        assert len(activities.json()) >= 1  # "created" activity
