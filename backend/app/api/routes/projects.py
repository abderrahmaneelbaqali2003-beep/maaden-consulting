"""Workflow Projet : CPS/CCTP -> exigences -> etude (moteur existant) -> scenarios ->
comparaison -> selection -> rapport. Reste volontairement mince : toute decision de
compatibilite reste dans `ConfigurationValidationService`/`run_recommendation` (existants,
jamais modifies) ; ce module ne fait qu'orchestrer l'entree (CPS -> `ProjectRequirement`)
et la sortie (etiquetage A/B/C + selection) autour de ces briques.
"""

import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.routes.recommendations import _component_ref, _documentary_analysis, _technical_calculations
from app.core.config import get_settings
from app.cps.analysis_service import CpsAnalysisService
from app.cps.service import CpsService, CpsDocumentNotFoundError, RequirementNotFoundError
from app.domain.history import log_project_event
from app.domain.requirements_analysis import FINAL_STATUSES, MissingMandatoryFieldsError, build_recommendation_request
from app.database.models import (
    CpsDocument,
    Driver,
    ExtractedRequirement,
    LedModule,
    Lens,
    Project,
    ProjectRequirement,
    ProjectScenario,
    RecommendationResult,
    RecommendationRun,
)
from app.reports.formatting import sanitize_filename
from app.reports.pdf_generator import PdfGenerator
from app.reports.report_service import ReportNotValidatedError, ReportResultNotFoundError, ReportService
from app.schemas.common import PaginatedResponse
from app.schemas.project import (
    CpsAnalysisResponse,
    CpsDocumentOut,
    ExtractedRequirementOut,
    ManualRequirementCreate,
    MissingFieldOut,
    ProjectCreate,
    ProjectOut,
    ProjectScenarioOut,
    ProjectUpdate,
    RequirementsAnalysisOut,
    RequirementUpdateRequest,
    ScenarioSelectRequest,
    StudyRunRequest,
)
from app.schemas.recommendation import RecommendationItem, ScoresOut
from app.services.recommendation_engine import run_recommendation

router = APIRouter(prefix="/api/projects", tags=["projects"])
logger = logging.getLogger(__name__)

SCENARIO_CODES = ["A", "B", "C", "D", "E"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _log(db: Session, project_id: int, action: str, actor: str | None = None, details: dict | None = None) -> None:
    log_project_event(db, project_id, action, actor=actor, details=details)


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return project


def _latest_run_scenarios(db: Session, project_id: int, run_type: str) -> list[ProjectScenario]:
    """Scenarios du run le plus recent d'un type donne (preliminary/final) pour un projet.
    Les runs plus anciens restent en base (tracabilite, section 14) mais ne sont plus
    "actifs" : relancer une pre-analyse plusieurs fois n'accumule jamais l'affichage."""
    latest = (
        db.query(ProjectScenario)
        .filter(ProjectScenario.project_id == project_id, ProjectScenario.run_type == run_type)
        .order_by(ProjectScenario.created_at.desc())
        .first()
    )
    if latest is None:
        return []
    latest_result = db.get(RecommendationResult, latest.recommendation_result_id)
    return (
        db.query(ProjectScenario)
        .join(RecommendationResult, ProjectScenario.recommendation_result_id == RecommendationResult.id)
        .filter(
            ProjectScenario.project_id == project_id,
            ProjectScenario.run_type == run_type,
            RecommendationResult.run_id == latest_result.run_id,
        )
        .order_by(ProjectScenario.scenario_code)
        .all()
    )


def _project_out(db: Session, project: Project) -> ProjectOut:
    cps_count = db.query(CpsDocument).filter(CpsDocument.project_id == project.id).count()
    requirement_count = db.query(ExtractedRequirement).filter(ExtractedRequirement.project_id == project.id).count()
    confirmed_count = (
        db.query(ExtractedRequirement)
        .filter(
            ExtractedRequirement.project_id == project.id,
            ExtractedRequirement.validation_status.in_(("confirmed", "modified", "manual")),
        )
        .count()
    )
    to_review_count = (
        db.query(ExtractedRequirement)
        .filter(ExtractedRequirement.project_id == project.id, ExtractedRequirement.validation_status == "detected")
        .count()
    )
    final_scenarios = _latest_run_scenarios(db, project.id, "final")
    preliminary_scenarios = _latest_run_scenarios(db, project.id, "preliminary")
    selected = next((s for s in final_scenarios if s.selected), None)
    return ProjectOut(
        id=project.id,
        reference=project.reference,
        name=project.name,
        client_name=project.client_name,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        cps_document_count=cps_count,
        requirement_count=requirement_count,
        requirements_confirmed_count=confirmed_count,
        requirements_to_review_count=to_review_count,
        preliminary_scenario_count=len(preliminary_scenarios),
        scenario_count=len(final_scenarios),
        selected_scenario_code=selected.scenario_code if selected else None,
    )


def _scenario_out(db: Session, scenario: ProjectScenario) -> ProjectScenarioOut:
    result = db.get(RecommendationResult, scenario.recommendation_result_id)
    run = db.get(RecommendationRun, result.run_id)
    requirement = db.get(ProjectRequirement, run.requirement_id) if run else None
    driver = db.get(Driver, result.driver_id)
    module = db.get(LedModule, result.module_id)
    lens = db.get(Lens, result.lens_id) if result.lens_id else None

    item = RecommendationItem(
        id=result.id,
        rank=result.rank,
        overall_score=result.overall_score,
        driver=_component_ref(driver),
        module=_component_ref(module),
        lens=_component_ref(lens) if lens else None,
        scores=ScoresOut(
            electrical=result.score_electrical,
            photometric=result.score_photometric,
            mechanical=result.score_mechanical,
            thermal=result.score_thermal,
            data_quality=result.score_data_quality,
        ),
        validated_rules=result.validated_rules,
        warnings=result.warnings,
        blocking_reasons=result.blocking_reasons,
        explanation=result.explanation,
        validation_status=result.validation_status,
        documentary_analysis=_documentary_analysis(result, db),
        technical_calculations=_technical_calculations(requirement, driver, module, lens),
    )
    return ProjectScenarioOut(
        id=scenario.id,
        project_id=scenario.project_id,
        scenario_code=scenario.scenario_code,
        run_type=scenario.run_type,
        selected=scenario.selected,
        selected_by=scenario.selected_by,
        selected_at=scenario.selected_at,
        selection_comment=scenario.selection_comment,
        recommendation=item,
        run_id=result.run_id,
    )


def _generate_reference(db: Session) -> str:
    year = _utcnow().year
    prefix = f"MC-PROJ-{year}-"
    count = db.query(Project).filter(Project.reference.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:04d}"


# ----------------------------------------------------------------------
# Projets
# ----------------------------------------------------------------------


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        reference=_generate_reference(db),
        name=payload.name,
        client_name=payload.client_name,
        description=payload.description,
        status="draft",
    )
    db.add(project)
    db.flush()
    _log(db, project.id, "project_created")
    db.commit()
    return _project_out(db, project)


@router.get("", response_model=PaginatedResponse[ProjectOut])
def list_projects(db: Session = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    query = db.query(Project).filter(Project.is_active.is_(True)).order_by(Project.created_at.desc())
    total = query.count()
    projects = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return PaginatedResponse(
        items=[_project_out(db, p) for p in projects], total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return _project_out(db, _get_project_or_404(db, project_id))


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in updates.items():
        setattr(project, field, value)
    db.commit()
    return _project_out(db, project)


# ----------------------------------------------------------------------
# CPS / CCTP
# ----------------------------------------------------------------------


@router.post("/{project_id}/documents/cps", response_model=CpsDocumentOut, status_code=201)
async def upload_cps_document(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    settings = get_settings()

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptes en V1.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Le fichier est vide.")
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Fichier trop volumineux (max {settings.max_upload_size_mb} Mo).")

    document = CpsService(db).import_document(project_id, file.filename, content)
    if project.status == "draft":
        project.status = "requirements_review"
    db.commit()
    return document


@router.get("/{project_id}/documents/cps", response_model=list[CpsDocumentOut])
def list_cps_documents(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    return (
        db.query(CpsDocument)
        .filter(CpsDocument.project_id == project_id)
        .order_by(CpsDocument.uploaded_at.desc())
        .all()
    )


# ----------------------------------------------------------------------
# Exigences extraites
# ----------------------------------------------------------------------


@router.post("/{project_id}/requirements/extract", response_model=list[ExtractedRequirementOut])
def extract_requirements(project_id: int, cps_document_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    try:
        rows = CpsService(db).extract_requirements(project_id, cps_document_id)
    except CpsDocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return rows


@router.get("/{project_id}/requirements", response_model=list[ExtractedRequirementOut])
def list_requirements(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    return (
        db.query(ExtractedRequirement)
        .filter(ExtractedRequirement.project_id == project_id)
        .order_by(ExtractedRequirement.category, ExtractedRequirement.field_name)
        .all()
    )


@router.post("/{project_id}/requirements", response_model=ExtractedRequirementOut, status_code=201)
def add_manual_requirement(project_id: int, payload: ManualRequirementCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    row = CpsService(db).add_manual_requirement(
        project_id, payload.category, payload.scope, payload.field_name, payload.operator, payload.value,
        payload.unit, payload.validated_by,
    )
    db.commit()
    return row


@router.patch("/{project_id}/requirements/{requirement_id}", response_model=ExtractedRequirementOut)
def update_requirement(
    project_id: int, requirement_id: int, payload: RequirementUpdateRequest, db: Session = Depends(get_db)
):
    _get_project_or_404(db, project_id)
    try:
        row = CpsService(db).update_requirement(
            project_id, requirement_id, payload.action, payload.validated_value, payload.validated_by
        )
    except RequirementNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return row


@router.post("/{project_id}/requirements/confirm", response_model=ProjectOut)
def confirm_requirements(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    pending = (
        db.query(ExtractedRequirement)
        .filter(ExtractedRequirement.project_id == project_id, ExtractedRequirement.validation_status == "detected")
        .count()
    )
    if pending:
        raise HTTPException(
            status_code=409,
            detail=f"{pending} exigence(s) detectee(s) restent a traiter (confirmer, modifier ou ignorer chacune).",
        )
    _log(db, project_id, "requirements_confirmed", details={})
    db.commit()
    return _project_out(db, project)


# ----------------------------------------------------------------------
# Pre-analyse automatique (CPS -> jusqu'a 3 configurations provisoires)
# ----------------------------------------------------------------------


@router.post("/{project_id}/cps/analyze", response_model=CpsAnalysisResponse, status_code=201)
async def analyze_cps_document(
    project_id: int, file: UploadFile = File(...), launched_by: str | None = Query(None), db: Session = Depends(get_db)
):
    """Action unique "Importer et analyser le CPS" : upload + extraction + pre-analyse
    automatique en un seul appel. Reutilise `CpsAnalysisService`, qui n'appelle lui-meme
    que `CpsService` et le moteur de recommandation existant (aucune duplication)."""
    project = _get_project_or_404(db, project_id)
    settings = get_settings()

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptes en V1.")
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Le fichier est vide.")
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Fichier trop volumineux (max {settings.max_upload_size_mb} Mo).")

    result = CpsAnalysisService(db).analyze_and_run_preliminary(project, file.filename, content, actor=launched_by)
    return CpsAnalysisResponse(
        document=result.document,
        requirements=result.requirements,
        analysis=RequirementsAnalysisOut(
            can_run_preliminary_study=result.analysis.can_run_study,
            missing_fields=[MissingFieldOut(field=m.field, label=m.label) for m in result.analysis.missing_fields],
            requirements_detected_count=result.analysis.requirements_detected_count,
            requirements_confirmed_count=result.analysis.requirements_confirmed_count,
            requirements_to_review_count=result.analysis.requirements_to_review_count,
        ),
        scenarios=[_scenario_out(db, s) for s in result.scenarios],
    )


@router.post("/{project_id}/cps/preliminary-study", response_model=CpsAnalysisResponse)
def rerun_preliminary_study(project_id: int, db: Session = Depends(get_db)):
    """Relance la pre-analyse SANS nouvel upload (ex: apres completion manuelle rapide
    des champs obligatoires manquants, section 9)."""
    project = _get_project_or_404(db, project_id)
    analysis, scenarios = CpsAnalysisService(db).run_preliminary_study(project)
    return CpsAnalysisResponse(
        analysis=RequirementsAnalysisOut(
            can_run_preliminary_study=analysis.can_run_study,
            missing_fields=[MissingFieldOut(field=m.field, label=m.label) for m in analysis.missing_fields],
            requirements_detected_count=analysis.requirements_detected_count,
            requirements_confirmed_count=analysis.requirements_confirmed_count,
            requirements_to_review_count=analysis.requirements_to_review_count,
        ),
        scenarios=[_scenario_out(db, s) for s in scenarios],
    )


# ----------------------------------------------------------------------
# Etude definitive / scenarios
# ----------------------------------------------------------------------


@router.post("/{project_id}/study/run", response_model=list[ProjectScenarioOut])
def run_study(project_id: int, payload: StudyRunRequest, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    try:
        request = build_recommendation_request(db, project_id, FINAL_STATUSES)
    except MissingMandatoryFieldsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    requirement = ProjectRequirement(**request.model_dump())
    db.add(requirement)
    db.flush()

    settings = get_settings()
    run = run_recommendation(db, requirement, settings)  # commite deja en interne
    run.run_type = "final"

    results = (
        db.query(RecommendationResult)
        .filter(RecommendationResult.run_id == run.id)
        .order_by(RecommendationResult.rank)
        .all()
    )

    scenarios = []
    for index, result in enumerate(results):
        scenario = ProjectScenario(
            project_id=project_id,
            recommendation_result_id=result.id,
            scenario_code=SCENARIO_CODES[index] if index < len(SCENARIO_CODES) else str(index + 1),
            selected=False,
            run_type="final",
        )
        db.add(scenario)
        scenarios.append(scenario)

    project.status = "scenario_selection" if scenarios else "study_in_progress"
    _log(db, project_id, "final_study_started", details={"run_id": run.id, "launched_by": payload.launched_by})
    _log(db, project_id, "final_scenarios_generated", details={"count": len(scenarios)})
    db.commit()

    return [_scenario_out(db, s) for s in scenarios]


@router.get("/{project_id}/scenarios", response_model=list[ProjectScenarioOut])
def list_scenarios(project_id: int, db: Session = Depends(get_db)):
    """Renvoie les scenarios du run PRELIMINAIRE le plus recent (s'il existe) suivis de
    ceux du run FINAL le plus recent (s'il existe) : jamais d'accumulation des anciennes
    pre-analyses (section 14), historique technique conserve en base."""
    _get_project_or_404(db, project_id)
    preliminary = _latest_run_scenarios(db, project_id, "preliminary")
    final = _latest_run_scenarios(db, project_id, "final")
    return [_scenario_out(db, s) for s in preliminary] + [_scenario_out(db, s) for s in final]


@router.get("/{project_id}/comparison", response_model=list[ProjectScenarioOut])
def get_comparison(project_id: int, db: Session = Depends(get_db)):
    """Comparaison de l'etude DEFINITIVE uniquement (la pre-analyse n'est jamais une
    base de comparaison/selection valable, voir section 3)."""
    _get_project_or_404(db, project_id)
    final = _latest_run_scenarios(db, project_id, "final")
    return [_scenario_out(db, s) for s in final]


@router.post("/{project_id}/scenarios/{scenario_id}/select", response_model=ProjectScenarioOut)
def select_scenario(project_id: int, scenario_id: int, payload: ScenarioSelectRequest, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    scenario = db.get(ProjectScenario, scenario_id)
    if scenario is None or scenario.project_id != project_id:
        raise HTTPException(status_code=404, detail="Scenario introuvable pour ce projet.")
    if scenario.run_type != "final":
        raise HTTPException(
            status_code=409,
            detail=(
                "Un scenario preliminaire ne peut pas etre selectionne comme decision finale. "
                "Validez d'abord les exigences puis lancez l'etude definitive."
            ),
        )

    others = (
        db.query(ProjectScenario)
        .filter(ProjectScenario.project_id == project_id, ProjectScenario.id != scenario_id)
        .all()
    )
    for other in others:
        other.selected = False

    scenario.selected = True
    scenario.selected_by = payload.selected_by
    scenario.selected_at = _utcnow()
    scenario.selection_comment = payload.selection_comment

    project.status = "photometric_validation"
    _log(
        db, project_id, "scenario_selected", actor=payload.selected_by,
        details={"scenario_code": scenario.scenario_code, "comment": payload.selection_comment},
    )
    db.commit()
    return _scenario_out(db, scenario)


# ----------------------------------------------------------------------
# Rapport final du projet (reutilise ReportService/PdfGenerator existants)
# ----------------------------------------------------------------------


@router.get("/{project_id}/report.pdf")
def get_project_report(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    scenario = (
        db.query(ProjectScenario)
        .filter(ProjectScenario.project_id == project_id, ProjectScenario.selected.is_(True))
        .first()
    )
    if scenario is None:
        raise HTTPException(status_code=409, detail="Aucun scenario n'a ete selectionne pour ce projet.")

    service = ReportService(db)
    try:
        report_data = service.build_report_data(scenario.recommendation_result_id)
    except ReportResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReportNotValidatedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        pdf_bytes = PdfGenerator().generate(report_data)
    except Exception:
        logger.exception("Echec de generation du rapport projet pour project_id=%s.", project_id)
        raise HTTPException(status_code=500, detail="Impossible de generer le rapport PDF.") from None

    content_hash = hashlib.sha256(pdf_bytes).hexdigest()
    try:
        service.record_generation(
            result_id=scenario.recommendation_result_id, reference=report_data.reference,
            generated_by=report_data.validation.validator_name, content_hash=content_hash, version="1.0",
        )
    except Exception:
        db.rollback()
        logger.warning("Tracabilite du rapport projet non enregistree (non bloquant).", exc_info=True)

    _log(db, project_id, "report_generated", details={"reference": report_data.reference})
    db.commit()

    filename = sanitize_filename(f"MAADEN_Consulting_Report_{report_data.reference}") + ".pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
