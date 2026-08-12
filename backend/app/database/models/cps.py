"""Modeles du pipeline CPS/CCTP -> exigences structurees (workflow Projet).

L'extraction est deterministe (regex/dictionnaires, `app/cps/extractor.py`) : ces tables ne
sont jamais alimentees par un LLM. Une exigence extraite reste TOUJOURS tracable jusqu'a sa
page/son extrait source (`source_page`/`source_excerpt`), et ne devient jamais une regle de
compatibilite tant qu'un consultant ne l'a pas confirmee (`ExtractedRequirement.validation_status`).
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class CpsDocument(TimestampMixin, Base):
    """Un fichier CPS/CCTP importe pour un projet."""

    __tablename__ = "cps_documents"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("consulting.projects.id", ondelete="CASCADE"), nullable=False)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)  # nom assaini sur disque
    document_type: Mapped[str] = mapped_column(String(20), default="pdf", nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # pending / extracted / insufficient_text / failed
    extraction_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    extraction_message: Mapped[str | None] = mapped_column(Text)


class CpsDocumentPage(Base):
    """Texte extrait d'une page d'un `CpsDocument` (extraction native, pas d'OCR en V1)."""

    __tablename__ = "cps_document_pages"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    cps_document_id: Mapped[int] = mapped_column(
        ForeignKey("consulting.cps_documents.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)


class ExtractedRequirement(TimestampMixin, Base):
    """Une exigence technique detectee dans un CPS, tracable et validee par un humain.

    `scope` distingue a QUOI s'applique l'exigence (driver / module / lens / luminaire /
    road / photometric / system / documentary) : une exigence IP66 "luminaire" ne doit
    jamais etre appliquee automatiquement au module LED (section 11 du besoin).
    """

    __tablename__ = "extracted_requirements"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("consulting.projects.id", ondelete="CASCADE"), nullable=False)
    cps_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("consulting.cps_documents.id", ondelete="SET NULL")
    )

    category: Mapped[str] = mapped_column(String(30), nullable=False)  # lighting/electrical/luminaire/geometry/...
    scope: Mapped[str] = mapped_column(String(30), nullable=False)
    field_name: Mapped[str] = mapped_column(String(60), nullable=False)
    operator: Mapped[str] = mapped_column(String(5), default="==", nullable=False)  # <=, >=, ==
    raw_value: Mapped[str] = mapped_column(String(255), nullable=False)
    numeric_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(20))

    source_page: Mapped[int | None] = mapped_column(Integer)
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    extraction_confidence: Mapped[str] = mapped_column(String(10), default="medium", nullable=False)  # high/medium/low

    # detected / confirmed / modified / ignored / manual
    validation_status: Mapped[str] = mapped_column(String(20), default="detected", nullable=False)
    validated_value: Mapped[str | None] = mapped_column(String(255))
    validated_by: Mapped[str | None] = mapped_column(String(150))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectScenario(TimestampMixin, Base):
    """Etiquette A/B/C d'un `RecommendationResult` au sein d'un projet.

    Ne duplique jamais les donnees du moteur : la compatibilite/le score restent
    exclusivement portes par `RecommendationResult`. Cette table ne fait que nommer
    et tracer la selection du consultant parmi les resultats d'une meme execution.
    """

    __tablename__ = "project_scenarios"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("consulting.projects.id", ondelete="CASCADE"), nullable=False)
    recommendation_result_id: Mapped[int] = mapped_column(
        ForeignKey("consulting.recommendation_results.id", ondelete="CASCADE"), nullable=False
    )
    scenario_code: Mapped[str] = mapped_column(String(1), nullable=False)  # A / B / C

    selected: Mapped[bool] = mapped_column(default=False, nullable=False)
    selected_by: Mapped[str | None] = mapped_column(String(150))
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selection_comment: Mapped[str | None] = mapped_column(Text)


class PhotometricValidation(TimestampMixin, Base):
    """Trace de la validation photometrique (DIALux) d'un scenario. V1 : saisie manuelle
    uniquement, aucune simulation automatisee."""

    __tablename__ = "photometric_validations"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("consulting.project_scenarios.id", ondelete="CASCADE"), nullable=False
    )

    dialux_status: Mapped[str] = mapped_column(String(20), default="not_started", nullable=False)
    ies_ldt_available: Mapped[bool] = mapped_column(default=False, nullable=False)
    simulation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    average_illuminance: Mapped[float | None] = mapped_column(Float)
    uniformity: Mapped[float | None] = mapped_column(Float)
    luminance: Mapped[float | None] = mapped_column(Float)
    ti_glare_index: Mapped[float | None] = mapped_column(Float)
    comment: Mapped[str | None] = mapped_column(Text)
    validated_by: Mapped[str | None] = mapped_column(String(150))


class ProjectHistory(Base):
    """Trace de tout evenement significatif au niveau du projet (jamais ecrasee)."""

    __tablename__ = "project_history"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("consulting.projects.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(150))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
