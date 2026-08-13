"""Orchestration de haut niveau du workflow CPS -> pre-analyse automatique.

`CpsAnalysisService` ne reimplemente RIEN : il appelle `CpsService` (import PDF,
extraction) puis delegue l'execution de la pre-analyse a `app.domain.preliminary_study`
(partagee avec l'assistant IA, voir `app/ai/orchestration.py` -- ni l'un ni l'autre ne
duplique cette logique ni ne depend du code de l'autre).

Deux etudes distinctes peuvent exister pour un meme projet (`RecommendationRun.run_type`) :
- "preliminary" : basee sur les exigences encore "detected" (pas de validation humaine
  requise), jamais selectionnable/rapportable -- sert uniquement d'apercu rapide.
- "final" : basee uniquement sur les exigences confirmees/modifiees/manuelles
  (inchangee, voir `api/routes/projects.py::run_study`).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.cps.service import CpsService
from app.database.models import CpsDocument, ExtractedRequirement, Project, ProjectScenario
from app.domain.preliminary_study import run_preliminary_study as _run_preliminary_study
from app.domain.requirements_analysis import RequirementsAnalysis

# Statuts de projet a partir desquels une pre-analyse fait progresser le workflow.
# Un projet deja plus avance (etude finale lancee, scenario selectionne...) ne doit
# jamais etre "retrogade" par une nouvelle pre-analyse.
_STATUSES_ADVANCED_BY_PRELIMINARY = {"draft", "requirements_review"}


@dataclass
class CpsAnalysisResult:
    document: CpsDocument | None
    requirements: list[ExtractedRequirement]
    analysis: RequirementsAnalysis
    scenarios: list[ProjectScenario]


class CpsAnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.cps_service = CpsService(db)

    def analyze_and_run_preliminary(
        self, project: Project, original_filename: str, content: bytes, actor: str | None = None
    ) -> CpsAnalysisResult:
        """Action unique "Importer et analyser le CPS" : upload + parse + extraction +
        pre-analyse, en un seul appel cote frontend."""
        document = self.cps_service.import_document(project.id, original_filename, content)

        requirements: list[ExtractedRequirement] = []
        if document.extraction_status == "extracted":
            requirements = self.cps_service.extract_requirements(project.id, document.id)

        if project.status in _STATUSES_ADVANCED_BY_PRELIMINARY:
            project.status = "preliminary_analysis"

        analysis, scenarios = self.run_preliminary_study(project, actor=actor)
        return CpsAnalysisResult(document=document, requirements=requirements, analysis=analysis, scenarios=scenarios)

    def run_preliminary_study(
        self, project: Project, actor: str | None = None
    ) -> tuple[RequirementsAnalysis, list[ProjectScenario]]:
        """Relance uniquement la pre-analyse (pas de nouvel upload) : utilisee apres
        completion manuelle rapide des champs obligatoires manquants."""
        return _run_preliminary_study(self.db, project, actor=actor)
