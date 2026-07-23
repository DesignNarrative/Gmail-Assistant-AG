import pytest

@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "strongpassword123"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/api/v1/auth/register", json={
        "email": "test2@example.com",
        "full_name": "Test User",
        "password": "strongpassword123"
    })
    response = await client.post("/api/v1/auth/register", json={
        "email": "test2@example.com",
        "full_name": "Test User",
        "password": "strongpassword123"
    })
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={
        "email": "test3@example.com",
        "full_name": "Test User",
        "password": "strongpassword123"
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "test3@example.com",
        "password": "strongpassword123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "test4@example.com",
        "full_name": "Test User",
        "password": "strongpassword123"
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "test4@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
