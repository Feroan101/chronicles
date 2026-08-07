from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chronicle.models.base import Base
from chronicle.utils.time import utcnow

if TYPE_CHECKING:
    from chronicle.models.confidence import ConfidenceScore
    from chronicle.models.evidence import Evidence
    from chronicle.models.project import Project
    from chronicle.models.relationship import Relationship


class Memory(Base):
    __tablename__ = "memories"
    __table_args__ = (UniqueConstraint("project_id", "id", name="uq_memories_project_id_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    type: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="memories")
    versions: Mapped[list[MemoryVersion]] = relationship(
        back_populates="memory", cascade="all, delete-orphan", order_by="MemoryVersion.sequence"
    )
    outgoing_relationships: Mapped[list[Relationship]] = relationship(
        foreign_keys="Relationship.from_memory_id", back_populates="source_memory"
    )
    incoming_relationships: Mapped[list[Relationship]] = relationship(
        foreign_keys="Relationship.to_memory_id", back_populates="target_memory"
    )


class MemoryVersion(Base):
    __tablename__ = "memory_versions"
    __table_args__ = (
        UniqueConstraint("memory_id", "sequence", name="uq_memory_versions_memory_id_sequence"),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    memory: Mapped[Memory] = relationship(back_populates="versions")
    evidence: Mapped[list[Evidence]] = relationship(
        back_populates="memory_version", cascade="all, delete-orphan"
    )
    confidence_scores: Mapped[list[ConfidenceScore]] = relationship(
        back_populates="memory_version", cascade="all, delete-orphan"
    )
