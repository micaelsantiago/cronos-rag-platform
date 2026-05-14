import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class WorkspaceCreate(BaseModel):
    name: str
    slug: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", v):
            raise ValueError("slug must contain only lowercase letters, numbers, and hyphens")
        return v


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip() if v else v

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", v):
            raise ValueError("slug must contain only lowercase letters, numbers, and hyphens")
        return v


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    owner_id: uuid.UUID
    plan: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkspaceWithRoleResponse(WorkspaceResponse):
    role: str


class MemberAddRequest(BaseModel):
    email: EmailStr
    role: Literal["member", "manager", "admin"] = "member"


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    role: str
    joined_at: datetime
    name: str
    email: str
