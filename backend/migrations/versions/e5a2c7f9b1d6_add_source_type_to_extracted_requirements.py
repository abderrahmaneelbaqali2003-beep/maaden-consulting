"""add source_type (cps/natural_language/manual) to extracted_requirements

Revision ID: e5a2c7f9b1d6
Revises: d3f6a8c1e9b4
Create Date: 2026-08-14 00:00:00.000000

V2 : le mode "Decrire mon besoin" (assistant IA / Groq) alimente la meme table
`extracted_requirements` que le CPS, avec source_type="natural_language". Cette colonne
permet de detecter un conflit entre deux sources contradictoires pour un meme champ
(ex: CPS = 4000K, description utilisateur = 3000K) sans jamais choisir automatiquement.

Backfill : toute ligne existante liee a un document (`cps_document_id` non nul) est
"cps" ; les autres (creees via l'ancien formulaire de saisie manuelle) sont "manual".
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a2c7f9b1d6"
down_revision: Union[str, None] = "d3f6a8c1e9b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "extracted_requirements",
        sa.Column("source_type", sa.String(length=20), nullable=False, server_default="cps"),
        schema="consulting",
    )
    op.execute(
        "UPDATE consulting.extracted_requirements SET source_type = 'manual' WHERE cps_document_id IS NULL"
    )


def downgrade() -> None:
    op.drop_column("extracted_requirements", "source_type", schema="consulting")
