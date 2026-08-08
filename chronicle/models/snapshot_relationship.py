from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chronicle.models.base import Base

if TYPE_CHECKING:
    from chronicle.models.snapshot import Snapshot


class SnapshotRelationship(Base):
    __tablename__ = "snapshot_relationships"

    snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("snapshots.id"), primary_key=True
    )
    relationship_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("relationships.id"), primary_key=True
    )
    from_memory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    to_memory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)

    snapshot: Mapped[Snapshot] = relationship(back_populates="snapshot_relationships")
