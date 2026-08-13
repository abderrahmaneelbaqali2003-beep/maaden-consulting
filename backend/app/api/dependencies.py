from app.ai.exceptions import GroqNotConfiguredError
from app.ai.groq_client import GroqClient
from app.ai.requirement_interpreter import GroqRequirementInterpreter, RequirementInterpreter
from app.core.config import get_settings
from app.database.session import get_db

__all__ = ["get_db", "get_requirement_interpreter"]


def get_requirement_interpreter() -> RequirementInterpreter:
    """Fournit l'implementation active de `RequirementInterpreter` (Protocol,
    app/ai/requirement_interpreter.py). Remplacee dans les tests via
    `app.dependency_overrides[get_requirement_interpreter]` (jamais de `MockRequirementInterpreter`
    construit ici : ce serait un double de test, pas un provider de production)."""
    settings = get_settings()
    if not settings.groq_enabled:
        raise GroqNotConfiguredError("L'assistant IA est desactive (GROQ_ENABLED=false).")
    if not settings.groq_api_key:
        raise GroqNotConfiguredError("Cle API Groq non configuree (GROQ_API_KEY).")
    return GroqRequirementInterpreter(GroqClient(settings))
