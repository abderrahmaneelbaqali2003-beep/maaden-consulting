from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class TraceabilityMixin:
    """Colonnes communes a tous les produits du catalogue (drivers, modules, lentilles).

    source_name: nom du fichier/feuille source de l'import.
    data_quality_score: score de completude/qualite calcule lors de l'import (0-100), repris de la source si present.
    data_quality_level: niveau qualitatif (high/medium/low/unusable) issu de la source.
    needs_manual_validation: True si une decision ne peut pas etre confirmee automatiquement (cf. section 21 du cahier des charges).
    is_active: suppression logique (soft delete).
    """

    source_name: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    data_quality_score: Mapped[float | None] = mapped_column()
    data_quality_level: Mapped[str | None] = mapped_column(String(20))
    needs_manual_validation: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
