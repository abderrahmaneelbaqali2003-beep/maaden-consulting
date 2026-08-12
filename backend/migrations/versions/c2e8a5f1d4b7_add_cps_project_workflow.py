"""add CPS import / extracted requirements / project scenarios workflow

Revision ID: c2e8a5f1d4b7
Revises: b7d4f1a9e6c3
Create Date: 2026-08-12 00:00:00.000000

Ajoute le pipeline Projet -> CPS/CCTP -> exigences extraites -> etude -> scenarios
(A/B/C) -> selection -> validation photometrique. Reutilise integralement le moteur
de recommandation V1/V2 existant : ces tables ne font que tracer/etiqueter des
`RecommendationResult` deja produits par `run_recommendation`, elles ne stockent
jamais de decision de compatibilite.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2e8a5f1d4b7"
down_revision: Union[str, None] = "b7d4f1a9e6c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("reference", sa.String(length=50), nullable=True), schema="consulting")
    op.create_unique_constraint("uq_consulting_projects_reference", "projects", ["reference"], schema="consulting")
    op.alter_column(
        "projects", "status", schema="consulting", server_default="draft", existing_type=sa.String(length=30)
    )

    op.create_table(
        "cps_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=20), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extraction_status", sa.String(length=30), nullable=False),
        sa.Column("extraction_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["consulting.projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="consulting",
    )
    op.create_index(
        "ix_consulting_cps_documents_project_id", "cps_documents", ["project_id"], schema="consulting"
    )

    op.create_table(
        "cps_document_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cps_document_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["cps_document_id"], ["consulting.cps_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="consulting",
    )
    op.create_index(
        "ix_consulting_cps_document_pages_cps_document_id",
        "cps_document_pages",
        ["cps_document_id"],
        schema="consulting",
    )

    op.create_table(
        "extracted_requirements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("cps_document_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("scope", sa.String(length=30), nullable=False),
        sa.Column("field_name", sa.String(length=60), nullable=False),
        sa.Column("operator", sa.String(length=5), nullable=False),
        sa.Column("raw_value", sa.String(length=255), nullable=False),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("extraction_confidence", sa.String(length=10), nullable=False),
        sa.Column("validation_status", sa.String(length=20), nullable=False),
        sa.Column("validated_value", sa.String(length=255), nullable=True),
        sa.Column("validated_by", sa.String(length=150), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["consulting.projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cps_document_id"], ["consulting.cps_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="consulting",
    )
    op.create_index(
        "ix_consulting_extracted_requirements_project_id",
        "extracted_requirements",
        ["project_id"],
        schema="consulting",
    )

    op.create_table(
        "project_scenarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("recommendation_result_id", sa.Integer(), nullable=False),
        sa.Column("scenario_code", sa.String(length=1), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("selected_by", sa.String(length=150), nullable=True),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("selection_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["consulting.projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["recommendation_result_id"], ["consulting.recommendation_results.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="consulting",
    )
    op.create_index(
        "ix_consulting_project_scenarios_project_id", "project_scenarios", ["project_id"], schema="consulting"
    )

    op.create_table(
        "photometric_validations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("dialux_status", sa.String(length=20), nullable=False),
        sa.Column("ies_ldt_available", sa.Boolean(), nullable=False),
        sa.Column("simulation_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("average_illuminance", sa.Float(), nullable=True),
        sa.Column("uniformity", sa.Float(), nullable=True),
        sa.Column("luminance", sa.Float(), nullable=True),
        sa.Column("ti_glare_index", sa.Float(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("validated_by", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["consulting.project_scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="consulting",
    )

    op.create_table(
        "project_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("actor", sa.String(length=150), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["consulting.projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="consulting",
    )
    op.create_index(
        "ix_consulting_project_history_project_id", "project_history", ["project_id"], schema="consulting"
    )


def downgrade() -> None:
    op.drop_index("ix_consulting_project_history_project_id", table_name="project_history", schema="consulting")
    op.drop_table("project_history", schema="consulting")

    op.drop_table("photometric_validations", schema="consulting")

    op.drop_index(
        "ix_consulting_project_scenarios_project_id", table_name="project_scenarios", schema="consulting"
    )
    op.drop_table("project_scenarios", schema="consulting")

    op.drop_index(
        "ix_consulting_extracted_requirements_project_id",
        table_name="extracted_requirements",
        schema="consulting",
    )
    op.drop_table("extracted_requirements", schema="consulting")

    op.drop_index(
        "ix_consulting_cps_document_pages_cps_document_id",
        table_name="cps_document_pages",
        schema="consulting",
    )
    op.drop_table("cps_document_pages", schema="consulting")

    op.drop_index("ix_consulting_cps_documents_project_id", table_name="cps_documents", schema="consulting")
    op.drop_table("cps_documents", schema="consulting")

    op.alter_column("projects", "status", schema="consulting", server_default="active", existing_type=sa.String(length=30))
    op.drop_constraint("uq_consulting_projects_reference", "projects", schema="consulting", type_="unique")
    op.drop_column("projects", "reference", schema="consulting")
