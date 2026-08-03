import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class RecommendationRun(TimestampMixin, Base):
    """Une execution du moteur de recommandation pour un jeu de besoins donne."""

    __tablename__ = "recommendation_runs"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("consulting.project_requirements.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(40), nullable=False)
    # compatible / compatible_with_warning / data_incomplete / manual_validation_required / not_compatible / impossible
    message: Mapped[str | None] = mapped_column(Text)

    drivers_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    modules_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lenses_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    blocking_reasons: Mapped[list] = mapped_column(JSON, default=list)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)


class RecommendationResult(TimestampMixin, Base):
    """Une configuration (driver + module + lentille) classee au sein d'une execution."""

    __tablename__ = "recommendation_results"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("consulting.recommendation_runs.id"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    driver_id: Mapped[int] = mapped_column(ForeignKey("catalog.drivers.id"), nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("catalog.led_modules.id"), nullable=False)
    lens_id: Mapped[int | None] = mapped_column(ForeignKey("catalog.lenses.id"))

    overall_score: Mapped[float] = mapped_column(nullable=False)
    score_electrical: Mapped[float] = mapped_column(nullable=False)
    score_photometric: Mapped[float] = mapped_column(nullable=False)
    score_mechanical: Mapped[float] = mapped_column(nullable=False)
    score_thermal: Mapped[float] = mapped_column(nullable=False)
    score_data_quality: Mapped[float] = mapped_column(nullable=False)

    validated_rules: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    blocking_reasons: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    validation_status: Mapped[str | None] = mapped_column(String(20))  # pending / validated / rejected
    validated_by: Mapped[str | None] = mapped_column(String(150))
