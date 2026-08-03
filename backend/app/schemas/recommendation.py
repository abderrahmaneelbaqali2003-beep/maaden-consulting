import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """Formulaire 'Nouveau calcul' (section 11). Les 5 premiers champs sont obligatoires."""

    project_id: int | None = None

    required_flux_lm: float = Field(..., gt=0, description="Flux lumineux demande (lm)")
    max_power_w: float = Field(..., gt=0, description="Puissance totale maximale autorisee (W)")
    required_cct_k: int = Field(..., gt=0, description="Temperature de couleur demandee (K)")
    voltage_nominal_v: float = Field(..., gt=0, description="Tension nominale du module (V)")
    current_nominal_ma: float = Field(..., gt=0, description="Courant nominal (mA)")

    protocol: str | None = Field(None, description="DALI, DALI-2, D4i, 0-10V ou 1-10V")
    led_package: str | None = None
    road_type: str | None = None
    pole_height_m: float | None = Field(None, gt=0)
    pole_spacing_m: float | None = Field(None, gt=0)
    ambient_temperature_c: float | None = None


class ComponentRef(BaseModel):
    id: int
    manufacturer: str
    reference: str


class ScoresOut(BaseModel):
    electrical: float
    photometric: float
    mechanical: float
    thermal: float
    data_quality: float


class RecommendationItem(BaseModel):
    rank: int
    overall_score: float
    driver: ComponentRef
    module: ComponentRef
    lens: ComponentRef | None
    scores: ScoresOut
    validated_rules: list[str]
    warnings: list[str]
    blocking_reasons: list[str]
    explanation: str
    validation_status: str | None = None


class RejectedSummary(BaseModel):
    drivers_rejected: int
    modules_rejected: int
    lenses_rejected: int


class RecommendationResponse(BaseModel):
    status: str
    request_id: uuid.UUID
    run_id: int
    message: str
    recommendations: list[RecommendationItem]
    rejected_summary: RejectedSummary
    blocking_reasons: list[str]
    suggestions: list[str]
    created_at: datetime


class ValidationDecision(BaseModel):
    validator_name: str | None = None
    comment: str | None = None
