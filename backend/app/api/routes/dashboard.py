from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.routes.recommendations import _build_response
from app.database.models import Driver, ImportHistory, LedModule, Lens, RecommendationRun
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

COMPATIBLE_STATUSES = {"compatible", "compatible_with_warning"}


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    drivers_count = db.query(Driver).filter(Driver.is_active.is_(True)).count()
    modules_count = db.query(LedModule).filter(LedModule.is_active.is_(True)).count()
    lenses_count = db.query(Lens).filter(Lens.is_active.is_(True)).count()

    runs = db.query(RecommendationRun).all()
    total_runs = len(runs)
    compatible_runs = sum(1 for r in runs if r.status in COMPATIBLE_STATUSES)
    compatible_rate = round(100 * compatible_runs / total_runs, 1) if total_runs else 0.0

    recent_imports = db.query(ImportHistory).order_by(ImportHistory.started_at.desc()).limit(5).all()
    recent_runs = db.query(RecommendationRun).order_by(RecommendationRun.created_at.desc()).limit(5).all()
    recent_recommendations = [_build_response(run, db) for run in recent_runs]

    return DashboardSummary(
        drivers_count=drivers_count,
        modules_count=modules_count,
        lenses_count=lenses_count,
        recommendation_runs_count=total_runs,
        compatible_rate_percent=compatible_rate,
        recent_imports=recent_imports,
        recent_recommendations=recent_recommendations,
    )
