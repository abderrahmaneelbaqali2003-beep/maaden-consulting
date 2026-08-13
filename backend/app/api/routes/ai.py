"""Assistant IA autonome : texte libre -> exigences structurees. Ne depend d'aucun
Projet ni du CPS (voir `app/ai/orchestration.py`). Le frontend construit ensuite un
`RecommendationRequest` a partir des champs renvoyes et appelle `POST /api/recommendations`
(meme moteur/endpoint que "Nouveau calcul") pour obtenir les configurations compatibles
a partir du catalogue en base -- l'IA ne calcule jamais elle-meme une compatibilite."""

from fastapi import APIRouter, Depends

from app.ai.orchestration import RequirementInterpretationService
from app.ai.requirement_interpreter import RequirementInterpreter
from app.api.dependencies import get_requirement_interpreter
from app.schemas.ai import (
    AiAmbiguousFieldOut,
    AiFieldOut,
    AiInterpretRequest,
    AiInterpretResponse,
    AiMissingFieldOut,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/interpret", response_model=AiInterpretResponse)
def interpret_text(
    payload: AiInterpretRequest,
    interpreter: RequirementInterpreter = Depends(get_requirement_interpreter),
) -> AiInterpretResponse:
    """`AIInterpretationError` (y compris levee par la dependance elle-meme, ex: Groq non
    configure) est convertie en 503 par le gestionnaire global (voir app/main.py)."""
    result = RequirementInterpretationService(interpreter).interpret(payload.text)

    return AiInterpretResponse(
        fields=[
            AiFieldOut(
                field_name=f.field_name,
                scope=f.scope,
                label=f.label,
                request_attr=f.request_attr,
                operator=f.operator,
                value=f.value,
                numeric_value=f.numeric_value,
                unit=f.unit,
                confidence=f.confidence,
                source_text=f.source_text,
            )
            for f in result.fields
        ],
        ambiguous_fields=[
            AiAmbiguousFieldOut(field_name=a.field_name, scope=a.scope, source_text=a.source_text, message=a.message)
            for a in result.ambiguous_fields
        ],
        summary=result.summary,
        missing_fields=[AiMissingFieldOut(request_attr=m.request_attr, label=m.label) for m in result.missing_fields],
        can_search=result.can_search,
    )
