from pydantic import BaseModel

from app.schemas.import_schema import ImportHistoryRead
from app.schemas.recommendation import RecommendationResponse


class DashboardSummary(BaseModel):
    drivers_count: int
    modules_count: int
    lenses_count: int
    recommendation_runs_count: int
    compatible_rate_percent: float
    recent_imports: list[ImportHistoryRead]
    recent_recommendations: list[RecommendationResponse]
