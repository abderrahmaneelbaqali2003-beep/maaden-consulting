"""Exceptions du module IA. Toutes heritent de `AIInterpretationError` : la route
appelante n'a besoin d'attraper qu'un seul type pour degrader proprement (503) sans
jamais faire planter l'application, quelle que soit la cause exacte de l'echec."""

AI_UNAVAILABLE_MESSAGE = (
    "L'analyse IA est temporairement indisponible. Vous pouvez continuer avec la saisie "
    "manuelle ou l'import CPS/CCTP."
)


class AIInterpretationError(Exception):
    """Base commune : l'assistant IA n'a pas pu produire d'exigences exploitables."""


class GroqNotConfiguredError(AIInterpretationError):
    """GROQ_ENABLED=false ou GROQ_API_KEY absente."""


class GroqTimeoutError(AIInterpretationError):
    """L'appel a depasse GROQ_TIMEOUT_SECONDS."""


class GroqUnavailableError(AIInterpretationError):
    """Erreur reseau ou reponse HTTP d'erreur (hors quota) de l'API Groq."""


class GroqQuotaExceededError(AIInterpretationError):
    """Reponse HTTP 429 (quota/limite de debit depassee)."""


class GroqInvalidResponseError(AIInterpretationError):
    """JSON invalide ou non conforme au schema `AIInterpretationResult` attendu."""
