from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    plan: Mapped[str] = mapped_column(String(50), nullable=False, server_default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    members: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan"
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, server_default="member")
    joined_at = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
