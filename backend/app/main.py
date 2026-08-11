from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    calculations,
    configurator,
    dashboard,
    drivers,
    imports,
    lenses,
    modules,
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


@app.get("/api/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "environment": settings.environment}
