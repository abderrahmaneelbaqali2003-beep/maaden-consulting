"""add run_type (preliminary/final) to recommendation_runs and project_scenarios

Revision ID: d3f6a8c1e9b4
Revises: c2e8a5f1d4b7
Create Date: 2026-08-13 00:00:00.000000

Permet de distinguer une pre-analyse automatique (jamais selectionnable/validable) de
l'etude definitive. Toutes les lignes existantes sont considerees "final" (comportement
historique inchange, seule l'etude finale existait avant cette migration).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3f6a8c1e9b4"
down_revision: Union[str, None] = "c2e8a5f1d4b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recommendation_runs",
        sa.Column("run_type", sa.String(length=20), nullable=False, server_default="final"),
        schema="consulting",
    )
    op.add_column(
        "project_scenarios",
        sa.Column("run_type", sa.String(length=20), nullable=False, server_default="final"),
        schema="consulting",
    )


def downgrade() -> None:
    op.drop_column("project_scenarios", "run_type", schema="consulting")
    op.drop_column("recommendation_runs", "run_type", schema="consulting")
