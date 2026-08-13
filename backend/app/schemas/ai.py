from pydantic import BaseModel, Field


class AiInterpretRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class AiFieldOut(BaseModel):
    field_name: str
    scope: str
    label: str
    request_attr: str  # attribut correspondant sur RecommendationRequest
    operator: str
    value: str | float | int | None
    numeric_value: float | None
    unit: str | None
    confidence: str
    source_text: str


class AiAmbiguousFieldOut(BaseModel):
    field_name: str | None
    scope: str | None
    source_text: str
    message: str


class AiMissingFieldOut(BaseModel):
    request_attr: str
    label: str


class AiInterpretResponse(BaseModel):
    fields: list[AiFieldOut]
    ambiguous_fields: list[AiAmbiguousFieldOut]
    # Recap redige par le modele IA de ce qu'il a compris du texte (jamais une
    # recommandation produit/score -- voir app/ai/prompts.py).
    summary: str | None
    missing_fields: list[AiMissingFieldOut]
    can_search: bool  # True si tous les champs obligatoires du moteur sont couverts
