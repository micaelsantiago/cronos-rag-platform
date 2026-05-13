import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_payload(suffix: str) -> dict:
    return {
        "name": f"User {suffix}",
        "email": f"{suffix}@example.com",
        "password": "password123",
    }


async def _register_and_login(client: AsyncClient, suffix: str) -> AsyncClient:
    """Registers and logs in, returning the client with cookies set."""
    await client.post("/api/v1/auth/register", json=_register_payload(suffix))
    await client.post(
        "/api/v1/auth/login",
        json={"email": f"{suffix}@example.com", "password": "password123"},
    )
    return client


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_creates_user(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/register", json=_register_payload("reg1"))
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "reg1@example.com"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_400(client: AsyncClient) -> None:
    payload = _register_payload("dup")
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_short_password_returns_422(client: AsyncClient) -> None:
    payload = {**_register_payload("short"), "password": "abc"}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_sets_httponly_cookies(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload("login1"))
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login1@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies
    # Response body must not contain tokens
    data = response.json()
    assert "access_token" not in data
    assert "refresh_token" not in data


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload("login2"))
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login2@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 401
    # Same error — doesn't reveal whether email exists
    assert response.json()["detail"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_lockout_after_5_failed_attempts(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload("lockout"))
    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "lockout@example.com", "password": "wrongpass"},
        )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "lockout@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 423
    detail = response.json()["detail"]
    assert detail["code"] == "ACCOUNT_LOCKED"
    assert "retry_after" in detail


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_without_auth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_authenticated_user(client: AsyncClient) -> None:
    await _register_and_login(client, "me1")
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "me1@example.com"


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_clears_cookies(client: AsyncClient) -> None:
    await _register_and_login(client, "logout1")
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    # After logout, /me must return 401
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
