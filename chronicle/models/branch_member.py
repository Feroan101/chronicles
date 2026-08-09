from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chronicle.models.base import Base
from chronicle.utils.time import utcnow

if TYPE_CHECKING:
    from chronicle.models.branch import Branch
    from chronicle.models.memory import Memory, MemoryVersion


class BranchMember(Base):
    __tablename__ = "branch_members"

    branch_id: Mapped[str] = mapped_column(String(36), ForeignKey("branches.id"), primary_key=True)
    memory_id: Mapped[str] = mapped_column(String(36), ForeignKey("memories.id"), primary_key=True)
    memory_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("memory_versions.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    branch: Mapped[Branch] = relationship(back_populates="members")
    memory: Mapped[Memory] = relationship(back_populates="branch_memberships")
    memory_version: Mapped[MemoryVersion] = relationship()
