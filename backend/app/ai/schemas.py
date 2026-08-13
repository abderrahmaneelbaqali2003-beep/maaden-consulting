"""Contrat de sortie structuree attendu du LLM (Groq). Rien de ce que le modele renvoie
n'est jamais fait confiance directement : cette validation Pydantic est la premiere
barriere, la liste blanche `app/domain/field_definitions.py` est la seconde (voir
`app/ai/requirement_interpreter.py`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AIExtractedRequirement(BaseModel):
    field_name: str
    scope: str
    operator: str = "=="
    value: str | float | int | None = None
    unit: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"
    source_text: str


class AIAmbiguousField(BaseModel):
    """Une expression du texte evoque une exigence sans valeur exacte exploitable
    (ex: "eclairage chaud") : le LLM ne doit JAMAIS deviner une valeur numerique dans
    ce cas, uniquement signaler l'ambiguite pour saisie manuelle par le consultant."""

    field_name: str | None = None
    scope: str | None = None
    source_text: str
    message: str


class AIInterpretationResult(BaseModel):
    requirements: list[AIExtractedRequirement] = Field(default_factory=list)
    ambiguous_fields: list[AIAmbiguousField] = Field(default_factory=list)
    # Recap en langage naturel de CE QUI A ETE COMPRIS (jamais une recommandation, un
    # score ou un nombre de configurations -- le LLM ne les connait pas). Optionnel :
    # un `MockRequirementInterpreter` de test peut ne pas le renseigner.
    summary: str | None = None
