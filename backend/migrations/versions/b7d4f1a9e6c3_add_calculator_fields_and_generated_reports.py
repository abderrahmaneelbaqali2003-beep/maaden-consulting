"""add calculator fields to project_requirements + generated_reports table

Revision ID: b7d4f1a9e6c3
Revises: a1c9e4d7f3b2
Create Date: 2026-08-11 00:00:00.000000

Ajoute les 5 champs du calculateur technique (geometrie routiere, implantation,
energie) a `consulting.project_requirements`, jusque-la utilises uniquement par
POST /api/calculations/preview et jamais persistes. Necessaire pour que le
rapport PDF de consulting puisse reconstruire l'etude complete depuis la base
(sans cela, les KPI geometrie/energie du rapport resteraient "non renseigne"
pour toute recommandation deja enregistree).

Ajoute egalement `consulting.generated_reports`, la table de tracabilite des
rapports PDF generes (reproductibilite : quelles donnees ont servi a generer
quel rapport, a quelle date, par qui).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d4f1a9e6c3"
down_revision: Union[str, None] = "a1c9e4d7f3b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project_requirements", sa.Column("road_width_m", sa.Float(), nullable=True), schema="consulting")
    op.add_column("project_requirements", sa.Column("road_length_m", sa.Float(), nullable=True), schema="consulting")
    op.add_column(
        "project_requirements", sa.Column("layout_type", sa.String(length=20), nullable=True), schema="consulting"
    )
    op.add_column(
        "project_requirements",
        sa.Column("operating_hours_per_year", sa.Float(), nullable=True),
        schema="consulting",
    )
    op.add_column(
        "project_requirements", sa.Column("energy_price_per_kwh", sa.Float(), nullable=True), schema="consulting"
    )

    op.create_table(
        "generated_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recommendation_result_id", sa.Integer(), nullable=False),
        sa.Column("report_reference", sa.String(length=50), nullable=False),
        sa.Column("report_type", sa.String(length=30), nullable=False),
        sa.Column("generated_by", sa.String(length=150), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=10), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["recommendation_result_id"], ["consulting.recommendation_results.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="consulting",
    )
    op.create_index(
        "ix_consulting_generated_reports_recommendation_result_id",
        "generated_reports",
        ["recommendation_result_id"],
        schema="consulting",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_consulting_generated_reports_recommendation_result_id",
        table_name="generated_reports",
        schema="consulting",
    )
    op.drop_table("generated_reports", schema="consulting")

    op.drop_column("project_requirements", "energy_price_per_kwh", schema="consulting")
    op.drop_column("project_requirements", "operating_hours_per_year", schema="consulting")
    op.drop_column("project_requirements", "layout_type", schema="consulting")
    op.drop_column("project_requirements", "road_length_m", schema="consulting")
    op.drop_column("project_requirements", "road_width_m", schema="consulting")
