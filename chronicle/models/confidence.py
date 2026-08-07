from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chronicle.models.base import Base
from chronicle.utils.time import utcnow

if TYPE_CHECKING:
    from chronicle.models.memory import MemoryVersion


class ConfidenceScore(Base):
    __tablename__ = "confidence_history"
    __table_args__ = (CheckConstraint("score >= 0.0 AND score <= 1.0", name="score_range"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    memory_version_id: Mapped[str] = mapped_column(ForeignKey("memory_versions.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    memory_version: Mapped[MemoryVersion] = relationship(back_populates="confidence_scores")
