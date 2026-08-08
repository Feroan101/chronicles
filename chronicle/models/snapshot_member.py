from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chronicle.models.base import Base

if TYPE_CHECKING:
    from chronicle.models.memory import MemoryVersion
    from chronicle.models.snapshot import Snapshot


class SnapshotMember(Base):
    __tablename__ = "snapshot_members"
    __table_args__ = {"schema": None}

    snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("snapshots.id"), primary_key=True
    )
    memory_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("memory_versions.id"), primary_key=True
    )

    snapshot: Mapped[Snapshot] = relationship(back_populates="members")
    memory_version: Mapped[MemoryVersion] = relationship()
