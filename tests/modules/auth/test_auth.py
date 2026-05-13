from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token
from app.modules.auth.models import RefreshToken, User


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


@pytest.mark.asyncio
async def test_register_empty_name_returns_422(client: AsyncClient) -> None:
    payload = {**_register_payload("emptyname"), "name": "   "}
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


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client: AsyncClient) -> None:
    await _register_and_login(client, "refresh1")
    old_refresh = client.cookies.get("refresh_token")
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert "access_token" in response.cookies
    new_refresh = response.cookies.get("refresh_token")
    assert new_refresh is not None
    assert new_refresh != old_refresh


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client: AsyncClient) -> None:
    client.cookies.set("refresh_token", "completelyfaketoken")
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_refresh_with_revoked_token_returns_401(client: AsyncClient) -> None:
    await _register_and_login(client, "refresh4")
    old_refresh = client.cookies.get("refresh_token")
    await client.post("/api/v1/auth/logout")
    # Re-inject the now-revoked token
    client.cookies.set("refresh_token", old_refresh)
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_refresh_with_expired_token_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register_and_login(client, "refresh5")
    raw_refresh = client.cookies.get("refresh_token")
    token_hash = hash_token(raw_refresh)

    past = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.execute(
        update(RefreshToken).where(RefreshToken.token_hash == token_hash).values(expires_at=past)
    )
    await db_session.commit()

    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "TOKEN_EXPIRED"


# ---------------------------------------------------------------------------
# Inactive user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_inactive_user_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload("inactive1"))
    await db_session.execute(
        update(User).where(User.email == "inactive1@example.com").values(is_active=False)
    )
    await db_session.commit()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive1@example.com", "password": "password123"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "ACCOUNT_DISABLED"


@pytest.mark.asyncio
async def test_refresh_with_deactivated_user_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register_and_login(client, "inactive2")
    # Deactivate user after issuing the token
    await db_session.execute(
        update(User).where(User.email == "inactive2@example.com").values(is_active=False)
    )
    await db_session.commit()
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_logout_without_cookie_returns_204(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 204
