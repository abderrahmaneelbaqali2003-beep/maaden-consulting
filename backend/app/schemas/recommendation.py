import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.calculations.models import CalculationResult


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

    # --- Calculateur technique (geometrie routiere / implantation / energie) ---
    road_width_m: float | None = Field(None, gt=0)
    road_length_m: float | None = Field(None, gt=0)
    layout_type: str | None = Field(None, description="unilateral, opposite, staggered ou central")
    operating_hours_per_year: float | None = Field(None, gt=0)
    energy_price_per_kwh: float | None = Field(None, gt=0)


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


class EvidenceOut(BaseModel):
    """Une preuve documentaire retrouvee pour une configuration retenue (V2 - RAG)."""

    category: str
    document: str
    section: str | None
    page: int | None
    relevance_score: float
    summary: str


class DocumentaryAnalysisOut(BaseModel):
    """Synthese documentaire d'une configuration (V2). Ne modifie jamais `overall_score`.

    `confidence` reste distincte de la compatibilite technique : une confiance
    documentaire basse ne signifie jamais qu'une configuration est incompatible.
    """

    confidence: str  # high / medium / low / insufficient_evidence
    evidence_count: int
    evidence: list[EvidenceOut]
    missing_evidence: list[str]


class RecommendationItem(BaseModel):
    id: int
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
    documentary_analysis: DocumentaryAnalysisOut | None = None
    technical_calculations: CalculationResult | None = None


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


class ValidateResultRequest(BaseModel):
    """Body de POST /api/recommendation-results/{result_id}/validate|reject.

    `validator_name` est obligatoire : une configuration validee sans nom de
    consultant ne doit jamais pouvoir produire un rapport PDF final.
    """

    validator_name: str = Field(..., min_length=1, description="Nom du consultant qui valide/rejette")
    comment: str | None = None
