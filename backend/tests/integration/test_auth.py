"""Integration tests for auth endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await client.post(
        "/v1/auth/register",
        json={
            "company_name": "Test Company",
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "user" in data
    assert "tokens" in data
    assert data["user"]["email"] == "test@example.com"
    assert data["tokens"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    # First registration
    await client.post(
        "/v1/auth/register",
        json={
            "company_name": "Company A",
            "email": "duplicate@example.com",
            "username": "user1",
            "password": "securepass123",
            "first_name": "User",
            "last_name": "One",
        },
    )

    # Duplicate registration
    response = await client.post(
        "/v1/auth/register",
        json={
            "company_name": "Company B",
            "email": "duplicate@example.com",
            "username": "user2",
            "password": "securepass123",
            "first_name": "User",
            "last_name": "Two",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register first
    await client.post(
        "/v1/auth/register",
        json={
            "company_name": "Login Test Co",
            "email": "login@example.com",
            "username": "loginuser",
            "password": "securepass123",
            "first_name": "Login",
            "last_name": "User",
        },
    )

    # Login
    response = await client.post(
        "/v1/auth/login",
        json={"email": "login@example.com", "password": "securepass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    response = await client.post(
        "/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    response = await client.get("/v1/auth/me")
    assert response.status_code in (401, 403)
