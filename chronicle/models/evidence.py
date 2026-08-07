from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chronicle.models.base import Base
from chronicle.utils.time import utcnow

if TYPE_CHECKING:
    from chronicle.models.memory import MemoryVersion


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    memory_version_id: Mapped[str] = mapped_column(ForeignKey("memory_versions.id"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(Text, nullable=False)
    ref: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    memory_version: Mapped[MemoryVersion] = relationship(back_populates="evidence")
