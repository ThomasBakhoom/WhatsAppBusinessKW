"""Unit tests for auth service."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthEndpoints:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/v1/auth/register", json={
            "email": "testauth@test.kw",
            "username": "testauth",
            "password": "TestPass123!",
            "company_name": "Test Auth Co",
            "first_name": "Test",
            "last_name": "Auth",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data["tokens"]
        assert data["user"]["email"] == "testauth@test.kw"

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {
            "email": "dup@test.kw", "username": "dup1", "password": "TestPass123!",
            "company_name": "Dup Co", "first_name": "D", "last_name": "U",
        }
        await client.post("/v1/auth/register", json=payload)
        resp = await client.post("/v1/auth/register", json={**payload, "username": "dup2"})
        assert resp.status_code in (409, 422, 500)

    async def test_login_success(self, client: AsyncClient):
        await client.post("/v1/auth/register", json={
            "email": "login@test.kw", "username": "loginuser", "password": "TestPass123!",
            "company_name": "Login Co", "first_name": "L", "last_name": "U",
        })
        resp = await client.post("/v1/auth/login", json={
            "email": "login@test.kw", "password": "TestPass123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/v1/auth/register", json={
            "email": "wrongpw@test.kw", "username": "wrongpw", "password": "TestPass123!",
            "company_name": "WP Co", "first_name": "W", "last_name": "P",
        })
        resp = await client.post("/v1/auth/login", json={
            "email": "wrongpw@test.kw", "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    async def test_me_with_token(self, client: AsyncClient):
        reg = await client.post("/v1/auth/register", json={
            "email": "me@test.kw", "username": "meuser", "password": "TestPass123!",
            "company_name": "Me Co", "first_name": "Me", "last_name": "User",
        })
        token = reg.json()["tokens"]["access_token"]
        resp = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user"]["email"] == "me@test.kw"

    async def test_me_without_token(self, client: AsyncClient):
        resp = await client.get("/v1/auth/me")
        assert resp.status_code in (401, 403)

    async def test_refresh_token(self, client: AsyncClient):
        reg = await client.post("/v1/auth/register", json={
            "email": "refresh@test.kw", "username": "refreshuser", "password": "TestPass123!",
            "company_name": "Refresh Co", "first_name": "R", "last_name": "T",
        })
        refresh = reg.json()["tokens"]["refresh_token"]
        resp = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        assert "access_token" in resp.json()
