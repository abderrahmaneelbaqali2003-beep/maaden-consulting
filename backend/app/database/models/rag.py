"""Modeles de la base documentaire normative (schema `rag`, V2).

Ces tables alimentent uniquement la couche de preuves documentaires
(`EvidenceEnrichmentService`) executee APRES le calcul des meilleures
configurations par le moteur deterministe. Elles ne participent jamais
au calcul de compatibilite, de scoring ou de classement.

Les embeddings sont stockes en JSONB (liste de floats) plutot que via
l'extension PostgreSQL `pgvector` : le corpus de cette V2 est volontairement
petit (2 documents), la similarite cosinus est donc calculee cote Python
(`app.rag.search.VectorSearchService`) sans necessiter de compilation
d'extension native. Si le corpus grossit significativement, migrer cette
colonne vers un type `Vector` pgvector reste possible sans changer l'API
des services de recherche.
"""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class RagDocument(TimestampMixin, Base):
    """Un document source indexe dans la base documentaire (V2 : les 2 PDF MAADEN)."""

    __tablename__ = "documents"
    __table_args__ = {"schema": "rag"}

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # official_standard / normative_guide / internal_summary / manufacturer_documentation
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    standard_family: Mapped[str | None] = mapped_column(String(60))
    domain: Mapped[str | None] = mapped_column(String(60))
    language: Mapped[str] = mapped_column(String(10), default="fr", nullable=False)

    source_type: Mapped[str | None] = mapped_column(String(40))
    # official / institutional / manufacturer / secondary
    authority_level: Mapped[str] = mapped_column(String(20), default="secondary", nullable=False)

    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    # pending / extracting / embedding / indexed / failed
    embedding_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)

    chunks: Mapped[list["RagDocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class RagDocumentChunk(TimestampMixin, Base):
    """Un passage indexe (texte + embedding) issu d'un `RagDocument`."""

    __tablename__ = "document_chunks"
    __table_args__ = {"schema": "rag"}

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("rag.documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSONB)

    document: Mapped["RagDocument"] = relationship(back_populates="chunks")
