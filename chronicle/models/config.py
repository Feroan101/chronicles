from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from chronicle.models.base import Base


class ConfigEntry(Base):
    __tablename__ = "config"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
