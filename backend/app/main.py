from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import configurator, dashboard, drivers, imports, lenses, modules, recommendations
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(
    title="Smart Lighting Decision Tool API",
    description="Outil d'aide a la decision pour le consulting en eclairage public.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drivers.router)
app.include_router(modules.router)
app.include_router(lenses.router)
app.include_router(recommendations.router)
app.include_router(imports.router)
app.include_router(dashboard.router)
app.include_router(configurator.router)


@app.get("/api/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "environment": settings.environment}
