import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.workspaces.models import Workspace, WorkspaceMember


@dataclass
class MemberRow:
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    role: str
    joined_at: datetime
    name: str
    email: str


class WorkspaceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, name: str, slug: str, owner_id: uuid.UUID) -> Workspace:
        workspace = Workspace(name=name, slug=slug, owner_id=owner_id)
        self.db.add(workspace)
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def get_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        result = await self.db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Workspace | None:
        result = await self.db.execute(
            select(Workspace).where(Workspace.slug == slug)
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        result = await self.db.execute(
            select(func.count()).select_from(Workspace).where(Workspace.slug == slug)
        )
        return (result.scalar() or 0) > 0

    async def update(self, workspace: Workspace, **kwargs: object) -> Workspace:
        for key, value in kwargs.items():
            setattr(workspace, key, value)
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def get_user_workspaces(
        self, user_id: uuid.UUID
    ) -> list[tuple[Workspace, WorkspaceMember]]:
        result = await self.db.execute(
            select(Workspace, WorkspaceMember)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(WorkspaceMember.joined_at.desc())
        )
        return list(result.all())


class WorkspaceMemberRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_member(
        self, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> WorkspaceMember | None:
        result = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def add(
        self, user_id: uuid.UUID, workspace_id: uuid.UUID, role: str
    ) -> WorkspaceMember:
        member = WorkspaceMember(user_id=user_id, workspace_id=workspace_id, role=role)
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove(self, member: WorkspaceMember) -> None:
        await self.db.delete(member)
        await self.db.commit()

    async def list_with_users(self, workspace_id: uuid.UUID) -> list[MemberRow]:
        result = await self.db.execute(
            select(
                WorkspaceMember.user_id,
                WorkspaceMember.workspace_id,
                WorkspaceMember.role,
                WorkspaceMember.joined_at,
                User.name,
                User.email,
            )
            .join(User, WorkspaceMember.user_id == User.id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.joined_at.asc())
        )
        return [
            MemberRow(
                user_id=row.user_id,
                workspace_id=row.workspace_id,
                role=row.role,
                joined_at=row.joined_at,
                name=row.name,
                email=row.email,
            )
            for row in result.all()
        ]

    async def count_admins(self, workspace_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == "admin",
            )
        )
        return result.scalar() or 0
