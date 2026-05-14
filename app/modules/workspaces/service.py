import re
import unicodedata
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.workspaces.models import Workspace, WorkspaceMember
from app.modules.workspaces.repository import MemberRow, WorkspaceMemberRepository, WorkspaceRepository

_ROLE_RANK = {"member": 0, "manager": 1, "admin": 2}


class WorkspaceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ws_repo = WorkspaceRepository(db)
        self.member_repo = WorkspaceMemberRepository(db)

    @staticmethod
    def _generate_slug(name: str) -> str:
        normalized = unicodedata.normalize("NFD", name)
        ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
        slug = ascii_name.lower()
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug.strip("-")
        return slug or "workspace"

    async def _resolve_slug(self, base_slug: str) -> str:
        if not await self.ws_repo.slug_exists(base_slug):
            return base_slug
        counter = 1
        while True:
            candidate = f"{base_slug}-{counter}"
            if not await self.ws_repo.slug_exists(candidate):
                return candidate
            counter += 1

    async def create(
        self, owner: User, name: str, requested_slug: str | None
    ) -> tuple[Workspace, str]:
        if requested_slug:
            if await self.ws_repo.slug_exists(requested_slug):
                raise HTTPException(status_code=409, detail="SLUG_ALREADY_EXISTS")
            slug = requested_slug
        else:
            base_slug = self._generate_slug(name)
            slug = await self._resolve_slug(base_slug)

        owner_id = uuid.UUID(str(owner.id))
        workspace = await self.ws_repo.create(name=name, slug=slug, owner_id=owner_id)
        await self.member_repo.add(
            user_id=owner_id,
            workspace_id=uuid.UUID(str(workspace.id)),
            role="admin",
        )
        return workspace, "admin"

    async def list_for_user(self, user_id: uuid.UUID) -> list[tuple[Workspace, str]]:
        rows = await self.ws_repo.get_user_workspaces(user_id)
        return [(ws, member.role) for ws, member in rows]

    async def get_for_user(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[Workspace, str]:
        workspace = await self.ws_repo.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="WORKSPACE_NOT_FOUND")

        member = await self.member_repo.get_member(user_id, workspace_id)
        if not member:
            raise HTTPException(status_code=403, detail="FORBIDDEN")

        return workspace, member.role

    async def update(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str | None,
        slug: str | None,
    ) -> tuple[Workspace, str]:
        workspace, role = await self.get_for_user(workspace_id, user_id)

        if role != "admin":
            raise HTTPException(status_code=403, detail="FORBIDDEN")

        updates: dict[str, object] = {}
        if name is not None:
            updates["name"] = name
        if slug is not None:
            existing = await self.ws_repo.get_by_slug(slug)
            if existing and uuid.UUID(str(existing.id)) != workspace_id:
                raise HTTPException(status_code=409, detail="SLUG_ALREADY_EXISTS")
            updates["slug"] = slug

        if updates:
            workspace = await self.ws_repo.update(workspace, **updates)

        return workspace, role

    async def list_members(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[MemberRow]:
        await self.get_for_user(workspace_id, user_id)
        return await self.member_repo.list_with_users(workspace_id)

    async def add_member(
        self,
        workspace_id: uuid.UUID,
        executor_id: uuid.UUID,
        email: str,
        role: str,
    ) -> MemberRow:
        _, executor_role = await self.get_for_user(workspace_id, executor_id)

        if _ROLE_RANK.get(executor_role, 0) < _ROLE_RANK["manager"]:
            raise HTTPException(status_code=403, detail="FORBIDDEN")

        if _ROLE_RANK.get(role, 0) > _ROLE_RANK.get(executor_role, 0):
            raise HTTPException(status_code=403, detail="INSUFFICIENT_ROLE")

        target_user = await UserRepository(self.db).get_by_email(email)
        if not target_user:
            raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

        target_id = uuid.UUID(str(target_user.id))
        if await self.member_repo.get_member(target_id, workspace_id):
            raise HTTPException(status_code=409, detail="MEMBER_ALREADY_EXISTS")

        await self.member_repo.add(target_id, workspace_id, role)
        rows = await self.member_repo.list_with_users(workspace_id)
        return next(r for r in rows if r.user_id == target_id)

    async def remove_member(
        self,
        workspace_id: uuid.UUID,
        executor_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        _, executor_role = await self.get_for_user(workspace_id, executor_id)

        if executor_role != "admin":
            raise HTTPException(status_code=403, detail="FORBIDDEN")

        target = await self.member_repo.get_member(target_user_id, workspace_id)
        if not target:
            raise HTTPException(status_code=404, detail="MEMBER_NOT_FOUND")

        if target.role == "admin" and await self.member_repo.count_admins(workspace_id) <= 1:
            raise HTTPException(status_code=422, detail="CANNOT_REMOVE_LAST_ADMIN")

        await self.member_repo.remove(target)
