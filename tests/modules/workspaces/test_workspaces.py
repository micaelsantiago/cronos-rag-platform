import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.api.dependencies.workspace import get_current_workspace
from app.modules.workspaces.models import Workspace

# ---------------------------------------------------------------------------
# Test-only route to exercise get_current_workspace (X-Workspace-ID header dep)
# Used in tests 8-10. Added once at module load time.
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends

_dep_test_router = APIRouter()


@_dep_test_router.get("/_test/ws-dep")
async def _ws_dep_probe(ws: Workspace = Depends(get_current_workspace)) -> dict:
    return {"id": str(ws.id), "name": ws.name}


app.include_router(_dep_test_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg(suffix: str) -> dict:
    return {
        "name": f"User {suffix}",
        "email": f"{suffix}@test.com",
        "password": "password123",
    }


async def _login(client: AsyncClient, suffix: str) -> None:
    """Register (if needed) and log in, leaving cookies on the client."""
    await client.post("/api/v1/auth/register", json=_reg(suffix))
    await client.post(
        "/api/v1/auth/login",
        json={"email": f"{suffix}@test.com", "password": "password123"},
    )


async def _create_ws(client: AsyncClient, name: str, slug: str | None = None) -> dict:
    payload: dict = {"name": name}
    if slug:
        payload["slug"] = slug
    response = await client.post("/api/v1/workspaces", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# CREATE workspace
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_workspace_creator_becomes_admin(client: AsyncClient) -> None:
    await _login(client, "creator_admin")
    ws = await _create_ws(client, "Acme Corp")

    assert ws["name"] == "Acme Corp"
    assert ws["role"] == "admin"
    assert ws["plan"] == "free"
    assert ws["is_active"] is True

    members_resp = await client.get(f"/api/v1/workspaces/{ws['id']}/members")
    assert members_resp.status_code == 200
    members = members_resp.json()
    assert len(members) == 1
    assert members[0]["role"] == "admin"
    assert members[0]["email"] == "creator_admin@test.com"


@pytest.mark.asyncio
async def test_create_workspace_auto_generates_slug(client: AsyncClient) -> None:
    await _login(client, "slug_auto")
    ws = await _create_ws(client, "My Company")
    assert ws["slug"] == "my-company"


@pytest.mark.asyncio
async def test_create_workspace_slug_with_accents_normalised(client: AsyncClient) -> None:
    await _login(client, "slug_accent")
    ws = await _create_ws(client, "Ação & Gestão")
    assert ws["slug"] == "acao-gestao"


@pytest.mark.asyncio
async def test_create_workspace_explicit_slug_collision_returns_409(
    client: AsyncClient,
) -> None:
    await _login(client, "slug_coll_a")
    await _create_ws(client, "First", slug="collide-me")

    # Second user uses same explicit slug
    await _login(client, "slug_coll_b")
    response = await client.post("/api/v1/workspaces", json={"name": "Second", "slug": "collide-me"})
    assert response.status_code == 409
    assert response.json()["detail"] == "SLUG_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_workspace_auto_slug_collision_adds_suffix(
    client: AsyncClient,
) -> None:
    await _login(client, "auto_coll_a")
    ws_a = await _create_ws(client, "Test Corp")
    assert ws_a["slug"] == "test-corp"

    await _login(client, "auto_coll_b")
    ws_b = await _create_ws(client, "Test Corp")
    assert ws_b["slug"] == "test-corp-1"


# ---------------------------------------------------------------------------
# LIST workspaces
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_workspaces_only_returns_own(client: AsyncClient) -> None:
    await _login(client, "list_a")
    await _create_ws(client, "Workspace A")

    await _login(client, "list_b")
    await _create_ws(client, "Workspace B")

    resp = await client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    names = [ws["name"] for ws in resp.json()]
    assert "Workspace B" in names
    assert "Workspace A" not in names


@pytest.mark.asyncio
async def test_list_workspaces_includes_role(client: AsyncClient) -> None:
    await _login(client, "list_role")
    await _create_ws(client, "Role Corp")

    resp = await client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    item = resp.json()[0]
    assert item["role"] == "admin"


# ---------------------------------------------------------------------------
# GET workspace by ID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_workspace_non_member_returns_403(client: AsyncClient) -> None:
    await _login(client, "get_ws_owner")
    ws = await _create_ws(client, "Private Corp")

    await _login(client, "get_ws_stranger")
    resp = await client.get(f"/api/v1/workspaces/{ws['id']}")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# get_current_workspace dependency (X-Workspace-ID header)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workspace_dep_missing_header_returns_400(client: AsyncClient) -> None:
    await _login(client, "dep_noheader")
    resp = await client.get("/api/v1/_test/ws-dep")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "X_WORKSPACE_ID_REQUIRED"


@pytest.mark.asyncio
async def test_workspace_dep_non_member_returns_403(client: AsyncClient) -> None:
    await _login(client, "dep_owner")
    ws = await _create_ws(client, "Exclusive Corp")

    await _login(client, "dep_outsider")
    resp = await client.get(
        "/api/v1/_test/ws-dep", headers={"X-Workspace-ID": ws["id"]}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_workspace_dep_inactive_workspace_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _login(client, "dep_inactive")
    ws = await _create_ws(client, "Dormant Corp")
    ws_id = uuid.UUID(ws["id"])

    await db_session.execute(
        sql_update(Workspace).where(Workspace.id == ws_id).values(is_active=False)
    )
    await db_session.commit()

    resp = await client.get(
        "/api/v1/_test/ws-dep", headers={"X-Workspace-ID": ws["id"]}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "WORKSPACE_INACTIVE"


# ---------------------------------------------------------------------------
# UPDATE workspace
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_workspace_admin_succeeds(client: AsyncClient) -> None:
    await _login(client, "upd_admin")
    ws = await _create_ws(client, "Old Name")

    resp = await client.put(
        f"/api/v1/workspaces/{ws['id']}",
        json={"name": "New Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_update_workspace_non_admin_returns_403(client: AsyncClient) -> None:
    await _login(client, "upd_owner")
    ws = await _create_ws(client, "Corp To Edit")

    # Add a regular member
    await _login(client, "upd_member_reg")
    # owner adds the member
    await _login(client, "upd_owner")
    await client.post(
        f"/api/v1/workspaces/{ws['id']}/members",
        json={"email": "upd_member_reg@test.com", "role": "member"},
    )

    # Member tries to update
    await _login(client, "upd_member_reg")
    resp = await client.put(
        f"/api/v1/workspaces/{ws['id']}",
        json={"name": "Hacked Name"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# MEMBERS — add / remove
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_member_duplicate_returns_409(client: AsyncClient) -> None:
    await _login(client, "dup_owner")
    ws = await _create_ws(client, "Dup Corp")

    await _login(client, "dup_target")
    await _login(client, "dup_owner")

    await client.post(
        f"/api/v1/workspaces/{ws['id']}/members",
        json={"email": "dup_target@test.com", "role": "member"},
    )
    resp = await client.post(
        f"/api/v1/workspaces/{ws['id']}/members",
        json={"email": "dup_target@test.com", "role": "member"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "MEMBER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_add_member_manager_cannot_add_admin(client: AsyncClient) -> None:
    await _login(client, "mgr_owner")
    ws = await _create_ws(client, "Manager Corp")

    # Register users first
    await _login(client, "mgr_manager")
    await _login(client, "mgr_target")

    # Owner adds a manager
    await _login(client, "mgr_owner")
    await client.post(
        f"/api/v1/workspaces/{ws['id']}/members",
        json={"email": "mgr_manager@test.com", "role": "manager"},
    )

    # Manager tries to add an admin
    await _login(client, "mgr_manager")
    resp = await client.post(
        f"/api/v1/workspaces/{ws['id']}/members",
        json={"email": "mgr_target@test.com", "role": "admin"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "INSUFFICIENT_ROLE"


@pytest.mark.asyncio
async def test_remove_last_admin_returns_422(client: AsyncClient) -> None:
    await _login(client, "last_admin")
    ws = await _create_ws(client, "Solo Admin Corp")

    me_resp = await client.get("/api/v1/auth/me")
    user_id = me_resp.json()["id"]

    resp = await client.delete(f"/api/v1/workspaces/{ws['id']}/members/{user_id}")
    assert resp.status_code == 422
    assert resp.json()["detail"] == "CANNOT_REMOVE_LAST_ADMIN"


@pytest.mark.asyncio
async def test_remove_member_succeeds(client: AsyncClient) -> None:
    await _login(client, "rm_owner")
    ws = await _create_ws(client, "Remove Corp")

    await _login(client, "rm_target")
    target_id = (await client.get("/api/v1/auth/me")).json()["id"]

    await _login(client, "rm_owner")
    await client.post(
        f"/api/v1/workspaces/{ws['id']}/members",
        json={"email": "rm_target@test.com", "role": "member"},
    )

    resp = await client.delete(f"/api/v1/workspaces/{ws['id']}/members/{target_id}")
    assert resp.status_code == 204

    members_resp = await client.get(f"/api/v1/workspaces/{ws['id']}/members")
    member_ids = [m["user_id"] for m in members_resp.json()]
    assert target_id not in member_ids
