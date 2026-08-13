"""Abstraction du provider d'interpretation (section 21 du besoin) : le moteur metier
ne depend jamais directement du SDK/de l'API Groq, uniquement de ce Protocol. Permet de
remplacer Groq par un autre provider LLM plus tard sans toucher a l'orchestration ni
aux routes."""

from __future__ import annotations

import json
import logging
import time
from typing import Protocol

from pydantic import ValidationError

from app.ai.exceptions import GroqInvalidResponseError
from app.ai.groq_client import GroqClient
from app.ai.prompts import build_system_prompt, build_user_prompt
from app.ai.schemas import AIInterpretationResult
from app.domain.field_definitions import FIELD_DEFINITIONS_BY_KEY

logger = logging.getLogger(__name__)


class RequirementInterpreter(Protocol):
    def interpret(self, text: str) -> AIInterpretationResult: ...


def _filter_to_whitelist(result: AIInterpretationResult) -> AIInterpretationResult:
    """Defense en profondeur : meme si le prompt l'interdit deja, toute exigence dont
    le couple (scope, field_name) n'est pas dans `field_definitions.py` est retiree
    silencieusement ici, avant que quoi que ce soit ne soit persiste ou utilise. C'est
    la protection determinante contre une injection de prompt (section 44)."""
    kept = [r for r in result.requirements if (r.scope, r.field_name) in FIELD_DEFINITIONS_BY_KEY]
    dropped = len(result.requirements) - len(kept)
    if dropped:
        logger.warning("Assistant IA : %d exigence(s) hors liste blanche ignoree(s).", dropped)
    result.requirements = kept
    return result


class GroqRequirementInterpreter:
    """Implementation Groq de `RequirementInterpreter`. Le SYSTEM_PROMPT interdit deja
    au modele de sortir du role d'extracteur (section 34) ; ce code ne fait jamais
    confiance au texte renvoye et revalide integralement via Pydantic + liste blanche."""

    def __init__(self, client: GroqClient):
        self.client = client

    def interpret(self, text: str) -> AIInterpretationResult:
        started = time.monotonic()
        success = False
        requirement_count = 0
        try:
            raw_content = self.client.chat_completion(build_system_prompt(), build_user_prompt(text))

            try:
                data = json.loads(raw_content)
            except json.JSONDecodeError as exc:
                raise GroqInvalidResponseError("Reponse IA non exploitable (JSON invalide).") from exc

            try:
                result = AIInterpretationResult.model_validate(data)
            except ValidationError as exc:
                raise GroqInvalidResponseError("Reponse IA non conforme au schema attendu.") from exc

            result = _filter_to_whitelist(result)
            requirement_count = len(result.requirements)
            success = True
            return result
        finally:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "Assistant IA (provider=groq, model=%s) : duree=%dms succes=%s exigences=%d",
                self.client.settings.groq_model, duration_ms, success, requirement_count,
            )


class MockRequirementInterpreter:
    """Interpreteur deterministe SANS reseau, utilise dans les tests (et injectable
    explicitement si besoin) : `canned` est renvoye tel quel (ou un resultat vide par
    defaut). Ne doit jamais etre utilise en dehors des tests -- `get_requirement_interpreter`
    (app/api/dependencies.py) ne construit jamais ce type par defaut."""

    def __init__(self, canned: AIInterpretationResult | None = None):
        self._canned = canned if canned is not None else AIInterpretationResult()

    def interpret(self, text: str) -> AIInterpretationResult:
        return _filter_to_whitelist(self._canned.model_copy(deep=True))
