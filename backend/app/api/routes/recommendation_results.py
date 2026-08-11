"""Validation/rejet d'une configuration precise (par `result_id`), et non plus
systematiquement du rang 1 de l'execution (bug corrige, voir `recommendations.py`
historique). Une configuration rejetee ne peut plus jamais etre validee ensuite
sans passer explicitement par /validate (et inversement)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.database.models import DecisionHistory, ExpertValidation, RecommendationResult
from app.schemas.recommendation import ValidateResultRequest

router = APIRouter(prefix="/api/recommendation-results", tags=["recommendation-results"])


def _get_result_or_404(result_id: int, db: Session) -> RecommendationResult:
    result = db.get(RecommendationResult, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Configuration recommandee introuvable.")
    return result


@router.post("/{result_id}/validate", status_code=200)
def validate_recommendation_result(result_id: int, payload: ValidateResultRequest, db: Session = Depends(get_db)):
    result = _get_result_or_404(result_id, db)

    result.validation_status = "validated"
    result.validated_by = payload.validator_name
    db.add(
        ExpertValidation(
            recommendation_result_id=result.id,
            validator_name=payload.validator_name,
            decision="validated",
            comment=payload.comment,
        )
    )
    db.add(
        DecisionHistory(
            recommendation_run_id=result.run_id,
            action="validated",
            actor=payload.validator_name,
            details={"recommendation_result_id": result.id},
        )
    )
    db.commit()
    return {"status": "validated", "recommendation_result_id": result.id}


@router.post("/{result_id}/reject", status_code=200)
def reject_recommendation_result(result_id: int, payload: ValidateResultRequest, db: Session = Depends(get_db)):
    result = _get_result_or_404(result_id, db)

    result.validation_status = "rejected"
    result.validated_by = payload.validator_name
    db.add(
        ExpertValidation(
            recommendation_result_id=result.id,
            validator_name=payload.validator_name,
            decision="rejected",
            comment=payload.comment,
        )
    )
    db.add(
        DecisionHistory(
            recommendation_run_id=result.run_id,
            action="rejected",
            actor=payload.validator_name,
            details={"recommendation_result_id": result.id},
        )
    )
    db.commit()
    return {"status": "rejected", "recommendation_result_id": result.id}
