"""Client HTTP minimal vers l'API Groq (compatible OpenAI). Aucun SDK tiers : un simple
appel `httpx` suffit et evite de lier toute l'application a un client proprietaire
(voir `requirement_interpreter.py` pour l'abstraction `RequirementInterpreter`, qui
permet de remplacer Groq par un autre provider sans toucher au moteur metier)."""

from __future__ import annotations

import logging

import httpx

from app.ai.exceptions import (
    GroqInvalidResponseError,
    GroqNotConfiguredError,
    GroqQuotaExceededError,
    GroqTimeoutError,
    GroqUnavailableError,
)
from app.core.config import Settings

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        """Renvoie le contenu texte (JSON attendu) du premier choix. Ne journalise
        jamais la cle API ni le contenu complet des messages (RGPD/confidentialite)."""
        if not self.settings.groq_enabled:
            raise GroqNotConfiguredError("L'assistant IA est desactive (GROQ_ENABLED=false).")
        if not self.settings.groq_api_key:
            raise GroqNotConfiguredError("Cle API Groq non configuree (GROQ_API_KEY).")

        try:
            response = httpx.post(
                GROQ_CHAT_COMPLETIONS_URL,
                headers={
                    "Authorization": f"Bearer {self.settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.settings.groq_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
                timeout=self.settings.groq_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise GroqTimeoutError(f"Delai depasse ({self.settings.groq_timeout_seconds}s) lors de l'appel Groq.") from exc
        except httpx.HTTPError as exc:
            raise GroqUnavailableError("API Groq injoignable.") from exc

        if response.status_code == 429:
            raise GroqQuotaExceededError("Quota/limite de debit Groq depasse.")
        if response.status_code >= 400:
            raise GroqUnavailableError(f"L'API Groq a repondu avec le statut {response.status_code}.")

        try:
            payload = response.json()
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise GroqInvalidResponseError("Reponse Groq inattendue (structure inconnue).") from exc
