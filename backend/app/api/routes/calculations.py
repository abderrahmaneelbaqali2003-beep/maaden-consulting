from fastapi import APIRouter

from app.calculations.models import CalculationInput, CalculationResult
from app.calculations.service import CalculationService

router = APIRouter(prefix="/api/calculations", tags=["calculations"])


@router.post("/preview", response_model=CalculationResult)
def preview_calculations(payload: CalculationInput) -> CalculationResult:
    """Calculateur technique (V1) : aucune dependance base de donnees, calcul pur.

    Independant du moteur de recommandation et de la base documentaire (RAG) :
    ne decide jamais de compatibilite, ne recherche jamais de reference normative.
    """
    return CalculationService().preview(payload)
