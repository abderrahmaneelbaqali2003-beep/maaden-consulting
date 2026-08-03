from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class SavedConfiguration(TimestampMixin, Base):
    """Configuration (driver + module + lentille) enregistree explicitement par un consultant,
    quel que soit le mode de selection utilise pour l'obtenir (automatic / manual / hybrid)."""

    __tablename__ = "saved_configurations"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("consulting.projects.id"))
    selection_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # automatic / manual / hybrid

    driver_id: Mapped[int | None] = mapped_column(ForeignKey("catalog.drivers.id"))
    module_id: Mapped[int] = mapped_column(ForeignKey("catalog.led_modules.id"), nullable=False)
    lens_id: Mapped[int | None] = mapped_column(ForeignKey("catalog.lenses.id"))

    status: Mapped[str] = mapped_column(String(40), nullable=False)
    overall_score: Mapped[float | None] = mapped_column()
    validated_rules: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    blocking_reasons: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    warnings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    user_comment: Mapped[str | None] = mapped_column(Text)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
