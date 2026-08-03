from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.database.models import (
    DecisionHistory,
    Driver,
    ExpertValidation,
    LedModule,
    Lens,
    ProjectRequirement,
    RecommendationResult,
    RecommendationRun,
)
from app.schemas.common import PaginatedResponse
from app.schemas.recommendation import (
    ComponentRef,
    RecommendationItem,
    RecommendationRequest,
    RecommendationResponse,
    RejectedSummary,
    ScoresOut,
    ValidationDecision,
)
from app.services.recommendation_engine import run_recommendation

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _component_ref(entity) -> ComponentRef:
    return ComponentRef(id=entity.id, manufacturer=entity.manufacturer.name, reference=entity.reference)


def _build_response(run: RecommendationRun, db: Session) -> RecommendationResponse:
    results = _fetch_results_with_relations(db, run.id)

    items = []
    for result in results:
        driver = db.get(Driver, result.driver_id)
        module = db.get(LedModule, result.module_id)
        lens = db.get(Lens, result.lens_id) if result.lens_id else None
        items.append(
            RecommendationItem(
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
            )
        )

    return RecommendationResponse(
        status=run.status,
        request_id=run.request_id,
        run_id=run.id,
        message=run.message or "",
        recommendations=items,
        rejected_summary=RejectedSummary(
            drivers_rejected=run.drivers_rejected,
            modules_rejected=run.modules_rejected,
            lenses_rejected=run.lenses_rejected,
        ),
        blocking_reasons=run.blocking_reasons or [],
        suggestions=run.suggestions or [],
        created_at=run.created_at,
    )


def _fetch_results_with_relations(db: Session, run_id: int) -> list[RecommendationResult]:
    return (
        db.query(RecommendationResult)
        .filter(RecommendationResult.run_id == run_id)
        .order_by(RecommendationResult.rank)
        .all()
    )


@router.post("", response_model=RecommendationResponse, status_code=201)
def create_recommendation(payload: RecommendationRequest, db: Session = Depends(get_db)):
    requirement = ProjectRequirement(
        project_id=payload.project_id,
        required_flux_lm=payload.required_flux_lm,
        max_power_w=payload.max_power_w,
        required_cct_k=payload.required_cct_k,
        voltage_nominal_v=payload.voltage_nominal_v,
        current_nominal_ma=payload.current_nominal_ma,
        protocol=payload.protocol,
        led_package=payload.led_package,
        road_type=payload.road_type,
        pole_height_m=payload.pole_height_m,
        pole_spacing_m=payload.pole_spacing_m,
        ambient_temperature_c=payload.ambient_temperature_c,
    )
    db.add(requirement)
    db.flush()

    settings = get_settings()
    run = run_recommendation(db, requirement, settings)

    db.add(DecisionHistory(recommendation_run_id=run.id, action="created", details={"status": run.status}))
    db.commit()

    return _build_response(run, db)


@router.get("/history", response_model=PaginatedResponse[RecommendationResponse])
def get_recommendation_history(
    db: Session = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
):
    query = db.query(RecommendationRun).order_by(RecommendationRun.created_at.desc())
    total = query.count()
    runs = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    items = [_build_response(run, db) for run in runs]
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/{run_id}", response_model=RecommendationResponse)
def get_recommendation(run_id: int, db: Session = Depends(get_db)):
    run = db.get(RecommendationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Execution de recommandation introuvable.")
    return _build_response(run, db)


@router.post("/{run_id}/validate", status_code=200)
def validate_recommendation(run_id: int, payload: ValidationDecision, db: Session = Depends(get_db)):
    run = db.get(RecommendationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Execution de recommandation introuvable.")
    top_result = (
        db.query(RecommendationResult)
        .filter(RecommendationResult.run_id == run_id)
        .order_by(RecommendationResult.rank)
        .first()
    )
    if top_result is None:
        raise HTTPException(status_code=404, detail="Aucune configuration a valider pour cette execution.")

    top_result.validation_status = "validated"
    top_result.validated_by = payload.validator_name
    db.add(
        ExpertValidation(
            recommendation_result_id=top_result.id,
            validator_name=payload.validator_name,
            decision="validated",
            comment=payload.comment,
        )
    )
    db.add(DecisionHistory(recommendation_run_id=run_id, action="validated", actor=payload.validator_name, details={}))
    db.commit()
    return {"status": "validated", "recommendation_result_id": top_result.id}


@router.post("/{run_id}/reject", status_code=200)
def reject_recommendation(run_id: int, payload: ValidationDecision, db: Session = Depends(get_db)):
    run = db.get(RecommendationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Execution de recommandation introuvable.")
    top_result = (
        db.query(RecommendationResult)
        .filter(RecommendationResult.run_id == run_id)
        .order_by(RecommendationResult.rank)
        .first()
    )
    if top_result is None:
        raise HTTPException(status_code=404, detail="Aucune configuration a rejeter pour cette execution.")

    top_result.validation_status = "rejected"
    top_result.validated_by = payload.validator_name
    db.add(
        ExpertValidation(
            recommendation_result_id=top_result.id,
            validator_name=payload.validator_name,
            decision="rejected",
            comment=payload.comment,
        )
    )
    db.add(DecisionHistory(recommendation_run_id=run_id, action="rejected", actor=payload.validator_name, details={}))
    db.commit()
    return {"status": "rejected", "recommendation_result_id": top_result.id}
