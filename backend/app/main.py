from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.exceptions import AI_UNAVAILABLE_MESSAGE, AIInterpretationError
from app.api.routes import (
    ai,
    calculations,
    configurator,
    dashboard,
    drivers,
    imports,
    lenses,
    modules,
    projects,
    rag,
    recommendation_results,
    recommendations,
    reports,
)
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(
    title="MAADEN Consulting API",
    description="Outil d'aide a la decision technique MAADEN Consulting pour l'eclairage public.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(drivers.router)
app.include_router(modules.router)
app.include_router(lenses.router)
app.include_router(recommendations.router)
app.include_router(imports.router)
app.include_router(dashboard.router)
app.include_router(configurator.router)
app.include_router(rag.router)
app.include_router(calculations.router)
app.include_router(recommendation_results.router)
app.include_router(reports.router)
app.include_router(projects.router)
app.include_router(ai.router)


@app.exception_handler(AIInterpretationError)
async def ai_interpretation_error_handler(request: Request, exc: AIInterpretationError) -> JSONResponse:
    """Filet de securite global : une erreur Groq peut survenir des la resolution de la
    dependance `get_requirement_interpreter` (avant meme le corps de la route), donc
    hors de portee d'un simple try/except local. Ne fait jamais planter l'application
    (jamais de 500) : degrade toujours vers un message clair (section 22 du besoin)."""
    return JSONResponse(status_code=503, content={"detail": AI_UNAVAILABLE_MESSAGE})


@app.get("/api/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "environment": settings.environment}
