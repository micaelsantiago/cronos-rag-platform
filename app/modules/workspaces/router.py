import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.schemas import (
    MemberAddRequest,
    MemberResponse,
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceWithRoleResponse,
)
from app.modules.workspaces.service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _to_response(workspace: Workspace, role: str) -> WorkspaceWithRoleResponse:
    return WorkspaceWithRoleResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        owner_id=workspace.owner_id,
        plan=workspace.plan,
        is_active=workspace.is_active,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        role=role,
    )


@router.post("", status_code=201, response_model=WorkspaceWithRoleResponse)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceWithRoleResponse:
    workspace, role = await WorkspaceService(db).create(current_user, data.name, data.slug)
    return _to_response(workspace, role)


@router.get("", response_model=list[WorkspaceWithRoleResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceWithRoleResponse]:
    pairs = await WorkspaceService(db).list_for_user(uuid.UUID(str(current_user.id)))
    return [_to_response(ws, role) for ws, role in pairs]


@router.get("/{workspace_id}", response_model=WorkspaceWithRoleResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceWithRoleResponse:
    workspace, role = await WorkspaceService(db).get_for_user(
        workspace_id, uuid.UUID(str(current_user.id))
    )
    return _to_response(workspace, role)


@router.put("/{workspace_id}", response_model=WorkspaceWithRoleResponse)
async def update_workspace(
    workspace_id: uuid.UUID,
    data: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceWithRoleResponse:
    workspace, role = await WorkspaceService(db).update(
        workspace_id, uuid.UUID(str(current_user.id)), data.name, data.slug
    )
    return _to_response(workspace, role)


@router.get("/{workspace_id}/members", response_model=list[MemberResponse])
async def list_members(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MemberResponse]:
    members = await WorkspaceService(db).list_members(
        workspace_id, uuid.UUID(str(current_user.id))
    )
    return [
        MemberResponse(
            user_id=m.user_id,
            workspace_id=m.workspace_id,
            role=m.role,
            joined_at=m.joined_at,
            name=m.name,
            email=m.email,
        )
        for m in members
    ]


@router.post("/{workspace_id}/members", status_code=201, response_model=MemberResponse)
async def add_member(
    workspace_id: uuid.UUID,
    data: MemberAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    member = await WorkspaceService(db).add_member(
        workspace_id, uuid.UUID(str(current_user.id)), data.email, data.role
    )
    return MemberResponse(
        user_id=member.user_id,
        workspace_id=member.workspace_id,
        role=member.role,
        joined_at=member.joined_at,
        name=member.name,
        email=member.email,
    )


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
async def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await WorkspaceService(db).remove_member(
        workspace_id, uuid.UUID(str(current_user.id)), user_id
    )
