"""add rag documents + recommendation evidence

Revision ID: a1c9e4d7f3b2
Revises: f2fb2296d1c6
Create Date: 2026-08-10 00:00:00.000000

V2 documentaire (RAG) : schema `rag` (documents, document_chunks) et table
`consulting.recommendation_evidence` reliant une configuration retenue a des
passages documentaires. N'affecte aucune table/colonne du moteur de
recommandation V1.

Les embeddings sont stockes en JSONB (liste de floats), pas via l'extension
PostgreSQL `pgvector` : le corpus de cette V2 est volontairement petit (2
documents), la similarite cosinus est calculee cote Python
(`app.rag.search.VectorSearchService`). Aucune extension native a installer/
compiler. Voir le docstring de `app.database.models.rag` pour la trajectoire
de migration vers `pgvector` si le corpus grossit significativement.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1c9e4d7f3b2"
down_revision: Union[str, None] = "f2fb2296d1c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS rag")

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("standard_family", sa.String(length=60), nullable=True),
        sa.Column("domain", sa.String(length=60), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=True),
        sa.Column("authority_level", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("embedding_status", sa.String(length=20), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_name"),
        schema="rag",
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section_title", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        # Liste de floats (embedding) stockee en JSONB : cf. docstring du module.
        sa.Column("embedding", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["rag.documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "content_hash", name="uq_document_chunk_dedup"),
        schema="rag",
    )
    op.create_index(
        "ix_document_chunks_document_id", "document_chunks", ["document_id"], schema="rag"
    )
    # Recherche plein texte francaise : combinee en RRF avec la similarite cosinus
    # calculee en Python (cf. app.rag.search.HybridRetrievalService).
    op.execute(
        "CREATE INDEX ix_document_chunks_content_fts ON rag.document_chunks "
        "USING GIN (to_tsvector('french', content))"
    )

    op.create_table(
        "recommendation_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recommendation_result_id", sa.Integer(), nullable=False),
        sa.Column("document_chunk_id", sa.Integer(), nullable=True),
        sa.Column("evidence_type", sa.String(length=40), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["recommendation_result_id"], ["consulting.recommendation_results.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["document_chunk_id"], ["rag.document_chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="consulting",
    )
    op.create_index(
        "ix_recommendation_evidence_result_id",
        "recommendation_evidence",
        ["recommendation_result_id"],
        schema="consulting",
    )


def downgrade() -> None:
    op.drop_index("ix_recommendation_evidence_result_id", table_name="recommendation_evidence", schema="consulting")
    op.drop_table("recommendation_evidence", schema="consulting")
    op.execute("DROP INDEX IF EXISTS rag.ix_document_chunks_content_fts")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks", schema="rag")
    op.drop_table("document_chunks", schema="rag")
    op.drop_table("documents", schema="rag")
