from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chronicle.models.base import Base
from chronicle.utils.time import utcnow

if TYPE_CHECKING:
    from chronicle.models.branch import Branch
    from chronicle.models.memory import Memory
    from chronicle.models.observation import Observation
    from chronicle.models.relationship import Relationship
    from chronicle.models.snapshot import Snapshot


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    default_branch_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("branches.id"), nullable=True
    )
    current_branch_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("branches.id"), nullable=True
    )

    branches: Mapped[list[Branch]] = relationship(
        back_populates="project",
        foreign_keys="Branch.project_id",
        cascade="all, delete-orphan",
    )

    memories: Mapped[list[Memory]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    relationships: Mapped[list[Relationship]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    observations: Mapped[list[Observation]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list[Snapshot]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
