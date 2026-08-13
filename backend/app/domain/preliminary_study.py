"""Execution d'une etude PRELIMINAIRE (apercu rapide, jamais selectionnable/rapportable)
a partir des exigences actuellement disponibles pour un projet (CPS ou saisie manuelle).
Reutilise strictement le moteur de recommandation existant (`run_recommendation`) --
aucune logique de compatibilite ou de scoring n'est dupliquee ici.

Vit dans `app/domain/` et non `app/cps/` pour rester reutilisable par tout mode de
saisie du besoin fonde sur `ExtractedRequirement`, sans que `app/cps/` n'ait a dependre
d'un autre package applicatif. L'assistant IA (`app/ai/`) n'appelle plus cette fonction :
il est autonome, ne cree aucune `ExtractedRequirement` et transmet ses exigences
directement a `POST /api/recommendations` (voir `app/ai/orchestration.py`).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models import Project, ProjectRequirement, ProjectScenario, RecommendationResult
from app.domain.history import log_project_event
from app.domain.requirements_analysis import PRELIMINARY_STATUSES, RequirementsAnalysis, analyze_readiness, build_recommendation_request
from app.services.recommendation_engine import run_recommendation

SCENARIO_CODES = ["A", "B", "C", "D", "E"]


def run_preliminary_study(
    db: Session, project: Project, actor: str | None = None
) -> tuple[RequirementsAnalysis, list[ProjectScenario]]:
    analysis = analyze_readiness(db, project.id, statuses=PRELIMINARY_STATUSES)

    if not analysis.can_run_study:
        log_project_event(
            db, project.id, "missing_data_detected",
            details={"missing_fields": [m.field for m in analysis.missing_fields]},
        )
        db.commit()
        return analysis, []

    request = build_recommendation_request(db, project.id, PRELIMINARY_STATUSES)
    requirement = ProjectRequirement(**request.model_dump())
    db.add(requirement)
    db.flush()

    settings = get_settings()
    log_project_event(db, project.id, "preliminary_study_started", actor=actor)
    run = run_recommendation(db, requirement, settings)  # reutilise le moteur existant, commite en interne
    run.run_type = "preliminary"

    results = (
        db.query(RecommendationResult)
        .filter(RecommendationResult.run_id == run.id)
        .order_by(RecommendationResult.rank)
        .all()
    )

    scenarios: list[ProjectScenario] = []
    for index, result in enumerate(results):
        scenario = ProjectScenario(
            project_id=project.id,
            recommendation_result_id=result.id,
            scenario_code=SCENARIO_CODES[index] if index < len(SCENARIO_CODES) else str(index + 1),
            selected=False,
            run_type="preliminary",
        )
        db.add(scenario)
        scenarios.append(scenario)

    log_project_event(db, project.id, "preliminary_scenarios_generated", details={"count": len(scenarios)})
    db.commit()
    return analysis, scenarios
