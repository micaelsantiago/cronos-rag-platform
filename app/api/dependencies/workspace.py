import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.repository import WorkspaceMemberRepository, WorkspaceRepository


async def get_current_workspace(
    x_workspace_id: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    if not x_workspace_id:
        raise HTTPException(status_code=400, detail="X_WORKSPACE_ID_REQUIRED")

    try:
        workspace_id = uuid.UUID(x_workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="INVALID_WORKSPACE_ID")

    workspace = await WorkspaceRepository(db).get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="WORKSPACE_NOT_FOUND")

    if not workspace.is_active:
        raise HTTPException(status_code=403, detail="WORKSPACE_INACTIVE")

    member = await WorkspaceMemberRepository(db).get_member(
        uuid.UUID(str(current_user.id)), workspace_id
    )
    if not member:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    return workspace
