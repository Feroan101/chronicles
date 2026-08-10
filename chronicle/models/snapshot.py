from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chronicle.models.base import Base
from chronicle.utils.time import utcnow

if TYPE_CHECKING:
    from chronicle.models.branch import Branch
    from chronicle.models.project import Project
    from chronicle.models.snapshot_member import SnapshotMember
    from chronicle.models.snapshot_relationship import SnapshotRelationship


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_snapshots_project_id_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("snapshots.id"), nullable=True
    )
    branch_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("branches.id"), nullable=True
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="snapshots")
    branch: Mapped[Branch | None] = relationship(back_populates="snapshots")
    parent: Mapped[Snapshot | None] = relationship(
        remote_side="Snapshot.id", back_populates="children"
    )
    children: Mapped[list[Snapshot]] = relationship(back_populates="parent")
    members: Mapped[list[SnapshotMember]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )
    snapshot_relationships: Mapped[list[SnapshotRelationship]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )
