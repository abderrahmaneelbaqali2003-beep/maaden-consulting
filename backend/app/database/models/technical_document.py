from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class TechnicalDocument(TimestampMixin, Base):
    """Fiche technique / fichier IES/LDT rattache a un produit du catalogue (extension future)."""

    __tablename__ = "technical_documents"
    __table_args__ = {"schema": "catalog"}

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # driver / led_module / lens
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)  # datasheet / ies / ldt / drawing
    file_name: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
