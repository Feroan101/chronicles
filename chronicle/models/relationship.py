from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chronicle.models.base import Base
from chronicle.utils.time import utcnow

if TYPE_CHECKING:
    from chronicle.models.memory import Memory
    from chronicle.models.project import Project


class Relationship(Base):
    __tablename__ = "relationships"
    __table_args__ = (CheckConstraint("from_memory_id <> to_memory_id", name="not_self"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    from_memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False)
    to_memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="relationships")
    source_memory: Mapped[Memory] = relationship(
        foreign_keys=[from_memory_id], back_populates="outgoing_relationships"
    )
    target_memory: Mapped[Memory] = relationship(
        foreign_keys=[to_memory_id], back_populates="incoming_relationships"
    )
