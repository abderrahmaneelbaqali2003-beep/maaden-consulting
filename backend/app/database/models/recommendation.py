import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

# evidence_type: road_lighting / photometric / driver_standard / module_standard /
#   luminaire_standard / lens_photometry / smart_lighting / safety / performance / measurement
# verification_status: retrieved / verified / manual_validation_required


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


class RecommendationEvidence(TimestampMixin, Base):
    """Preuve documentaire (RAG) reliee a une configuration retenue dans le TOP final.

    Generee uniquement par `EvidenceEnrichmentService`, apres coup, a partir d'une
    recherche dans `rag.document_chunks`. Ne modifie jamais la compatibilite ni le
    score technique du `RecommendationResult` associe.

    `document_chunk_id` est nullable : une ligne "sentinelle" (`evidence_type
    ="missing_evidence"`, `document_chunk_id=None`) sert a persister une
    validation documentaire manquante (ex: "Simulation DIALux non realisee"),
    sans avoir a alterer le schema de `recommendation_results` (table V1).
    """

    __tablename__ = "recommendation_evidence"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_result_id: Mapped[int] = mapped_column(
        ForeignKey("consulting.recommendation_results.id", ondelete="CASCADE"), nullable=False
    )
    document_chunk_id: Mapped[int | None] = mapped_column(
        ForeignKey("rag.document_chunks.id", ondelete="CASCADE")
    )

    # road_lighting / photometric / driver_standard / module_standard / luminaire_standard /
    # lens_photometry / smart_lighting / safety / performance / measurement / missing_evidence
    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float] = mapped_column(nullable=False)
    # retrieved / verified / manual_validation_required
    verification_status: Mapped[str] = mapped_column(String(30), default="retrieved", nullable=False)
