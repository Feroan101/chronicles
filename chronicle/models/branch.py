from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chronicle.models.base import Base
from chronicle.utils.time import utcnow

if TYPE_CHECKING:
    from chronicle.models.branch_member import BranchMember
    from chronicle.models.project import Project
    from chronicle.models.snapshot import Snapshot


class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_branches_project_id_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="branches", foreign_keys=[project_id])
    members: Mapped[list[BranchMember]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list[Snapshot]] = relationship(back_populates="branch")
