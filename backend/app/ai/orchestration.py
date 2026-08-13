"""Interpretation autonome d'une description en langage naturel : texte -> exigences
structurees, sans lire ni ecrire aucune donnee Projet/CPS (pas de session DB ici).

Le LLM n'est jamais la source de verite sur la compatibilite, le score ou la conformite :
il extrait uniquement des exigences depuis le texte fourni. Ces exigences sont ensuite
transmises telles quelles (par l'appelant) au moteur de recommandation existant via
`POST /api/recommendations` -- exactement le meme endpoint que la saisie manuelle
("Nouveau calcul") -- qui reste seul a decider driver/module/lentille compatibles a
partir du catalogue en base."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.requirement_interpreter import RequirementInterpreter
from app.ai.schemas import AIAmbiguousField
from app.domain.field_definitions import FIELD_DEFINITIONS_BY_KEY, MANDATORY_ATTR_LABELS, MANDATORY_REQUEST_ATTRS


@dataclass
class InterpretedField:
    field_name: str
    scope: str
    label: str
    request_attr: str
    operator: str
    value: str | float | int | None
    numeric_value: float | None
    unit: str | None
    confidence: str
    source_text: str


@dataclass
class MissingMandatoryField:
    request_attr: str
    label: str


@dataclass
class InterpretationResult:
    fields: list[InterpretedField]
    ambiguous_fields: list[AIAmbiguousField]
    summary: str | None
    missing_fields: list[MissingMandatoryField]
    can_search: bool


class RequirementInterpretationService:
    """Aucune dependance a `app.cps.*` ni `app.database.*` : ce service ne fait que
    transformer la sortie deja validee/filtree de `RequirementInterpreter` en une forme
    directement exploitable par l'appelant pour construire un `RecommendationRequest`."""

    def __init__(self, interpreter: RequirementInterpreter):
        self.interpreter = interpreter

    def interpret(self, text: str) -> InterpretationResult:
        interpretation = self.interpreter.interpret(text)

        fields: list[InterpretedField] = []
        covered_attrs: set[str] = set()
        for item in interpretation.requirements:
            definition = FIELD_DEFINITIONS_BY_KEY.get((item.scope, item.field_name))
            if definition is None:
                continue  # liste blanche : defense en profondeur (deja filtre par l'interpreteur)

            numeric_value = item.value if isinstance(item.value, (int, float)) else None
            fields.append(
                InterpretedField(
                    field_name=item.field_name,
                    scope=item.scope,
                    label=definition.label,
                    request_attr=definition.request_attr,
                    operator=item.operator or "==",
                    value=item.value,
                    numeric_value=numeric_value,
                    unit=item.unit,
                    confidence=item.confidence,
                    source_text=item.source_text,
                )
            )
            if item.value is not None:
                covered_attrs.add(definition.request_attr)

        missing = [
            MissingMandatoryField(request_attr=attr, label=MANDATORY_ATTR_LABELS[attr])
            for attr in MANDATORY_REQUEST_ATTRS
            if attr not in covered_attrs
        ]

        return InterpretationResult(
            fields=fields,
            ambiguous_fields=interpretation.ambiguous_fields,
            summary=interpretation.summary,
            missing_fields=missing,
            can_search=not missing,
        )
