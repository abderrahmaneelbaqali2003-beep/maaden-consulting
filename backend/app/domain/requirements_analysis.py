"""Analyse de suffisance des exigences et construction du `RecommendationRequest`.

Extrait de `CpsService` pour vivre dans la couche neutre `app/domain/` : cette logique
n'a rien de specifique au CPS (elle lit `ExtractedRequirement` quelle que soit son
origine -- `source_type` cps/manual). L'assistant IA (`app/ai/`) ne l'utilise plus : il
est autonome et ne cree aucune `ExtractedRequirement`.

Deux niveaux de lecture des exigences (jamais melanges) :
- PRELIMINARY_STATUSES (inclut "detected") : utilise UNIQUEMENT pour une pre-analyse
  automatique, avant toute validation humaine.
- FINAL_STATUSES (confirmed/modified/manual) : utilise pour l'etude definitive, la
  seule dont le resultat peut etre selectionne/valide/rapporte.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database.models import ExtractedRequirement
from app.domain.field_definitions import (
    MANDATORY_ATTR_LABELS,
    MANDATORY_REQUEST_ATTRS,
    NUMERIC_REQUEST_ATTRS,
    REQUEST_FIELD_MAP,
)
from app.schemas.recommendation import RecommendationRequest

PRELIMINARY_STATUSES: tuple[str, ...] = ("detected", "confirmed", "modified", "manual")
FINAL_STATUSES: tuple[str, ...] = ("confirmed", "modified", "manual")


@dataclass
class MissingField:
    field: str
    label: str


@dataclass
class RequirementsAnalysis:
    can_run_study: bool
    missing_fields: list[MissingField]
    requirements_detected_count: int
    requirements_confirmed_count: int
    requirements_to_review_count: int


class MissingMandatoryFieldsError(Exception):
    def __init__(self, missing_fields: list[str]):
        self.missing_fields = missing_fields
        labels = ", ".join(MANDATORY_ATTR_LABELS.get(f, f) for f in missing_fields)
        super().__init__(f"Champs obligatoires manquants pour lancer l'etude : {labels}.")


def collect_values(db: Session, project_id: int, statuses: tuple[str, ...]) -> dict[str, object]:
    rows = (
        db.query(ExtractedRequirement)
        .filter(
            ExtractedRequirement.project_id == project_id,
            ExtractedRequirement.validation_status.in_(statuses),
        )
        .all()
    )
    values: dict[str, object] = {}
    for row in rows:
        attr = REQUEST_FIELD_MAP.get((row.scope, row.field_name))
        if attr is None:
            continue
        effective_raw = row.validated_value or row.raw_value
        if attr in NUMERIC_REQUEST_ATTRS:
            if row.numeric_value is not None:
                values[attr] = row.numeric_value
        else:
            values[attr] = effective_raw
    return values


def analyze_readiness(
    db: Session, project_id: int, statuses: tuple[str, ...] = PRELIMINARY_STATUSES
) -> RequirementsAnalysis:
    """Determine si une etude (preliminaire par defaut) est lancable avec les
    exigences actuellement disponibles, sans jamais modifier leur statut."""
    values = collect_values(db, project_id, statuses)
    missing = [MissingField(attr, MANDATORY_ATTR_LABELS[attr]) for attr in MANDATORY_REQUEST_ATTRS if attr not in values]

    detected_count = db.query(ExtractedRequirement).filter(ExtractedRequirement.project_id == project_id).count()
    confirmed_count = (
        db.query(ExtractedRequirement)
        .filter(ExtractedRequirement.project_id == project_id, ExtractedRequirement.validation_status.in_(FINAL_STATUSES))
        .count()
    )
    to_review_count = (
        db.query(ExtractedRequirement)
        .filter(ExtractedRequirement.project_id == project_id, ExtractedRequirement.validation_status == "detected")
        .count()
    )

    return RequirementsAnalysis(
        can_run_study=not missing,
        missing_fields=missing,
        requirements_detected_count=detected_count,
        requirements_confirmed_count=confirmed_count,
        requirements_to_review_count=to_review_count,
    )


def build_recommendation_request(db: Session, project_id: int, statuses: tuple[str, ...]) -> RecommendationRequest:
    values = collect_values(db, project_id, statuses)
    missing = [attr for attr in MANDATORY_REQUEST_ATTRS if attr not in values]
    if missing:
        raise MissingMandatoryFieldsError(missing)

    if "required_cct_k" in values:
        values["required_cct_k"] = int(values["required_cct_k"])

    return RecommendationRequest(project_id=project_id, **values)
