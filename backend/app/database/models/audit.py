from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class ImportHistory(TimestampMixin, Base):
    """Historique de chaque import de fichier Excel/CSV (section 9 du cahier des charges)."""

    __tablename__ = "import_history"
    __table_args__ = {"schema": "audit"}

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # driver / led_module / lens
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64))
    rows_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # success / partial / failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class DataIssue(TimestampMixin, Base):
    """Anomalie detectee ligne par ligne lors d'un import (peut aussi etre chargee depuis
    les feuilles data_issues des fichiers sources lors de l'import initial)."""

    __tablename__ = "data_issues"
    __table_args__ = {"schema": "audit"}

    id: Mapped[int] = mapped_column(primary_key=True)
    import_history_id: Mapped[int | None] = mapped_column(ForeignKey("audit.import_history.id"))
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_external_ref: Mapped[str | None] = mapped_column(String(20))
    row_number: Mapped[int | None] = mapped_column(Integer)
    column_name: Mapped[str | None] = mapped_column(String(150))
    issue_category: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # high / medium / low / information
    recommended_action: Mapped[str | None] = mapped_column(Text)
    manual_review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)


class ExpertValidation(TimestampMixin, Base):
    """Validation/rejet manuel d'une recommandation par un consultant (endpoints /validate, /reject)."""

    __tablename__ = "expert_validations"
    __table_args__ = {"schema": "audit"}

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_result_id: Mapped[int] = mapped_column(
        ForeignKey("consulting.recommendation_results.id"), nullable=False
    )
    validator_name: Mapped[str | None] = mapped_column(String(150))
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # validated / rejected
    comment: Mapped[str | None] = mapped_column(Text)


class DecisionHistory(TimestampMixin, Base):
    """Trace de toute action significative sur une execution de recommandation."""

    __tablename__ = "decision_history"
    __table_args__ = {"schema": "audit"}

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_run_id: Mapped[int] = mapped_column(
        ForeignKey("consulting.recommendation_runs.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # created / validated / rejected / exported
    actor: Mapped[str | None] = mapped_column(String(150))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
