from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.recommendation import ComponentRef, ScoresOut


class PartialRequirements(BaseModel):
    """Besoins projet pour le configurateur manuel/semi-automatique.

    Contrairement a `RecommendationRequest` (mode automatique), TOUS les champs sont
    optionnels ici : un consultant doit pouvoir valider une combinaison qu'il connait
    deja sans ressaisir l'integralite du besoin (cf. exemple `project_requirements: {}`
    de la demande). Les champs absents degradent le score/les criteres correspondants
    en "non verifiable" plutot que de bloquer l'appel.
    """

    required_flux_lm: float | None = Field(None, gt=0)
    max_power_w: float | None = Field(None, gt=0)
    required_cct_k: int | None = Field(None, gt=0)
    voltage_nominal_v: float | None = Field(None, gt=0)
    current_nominal_ma: float | None = Field(None, gt=0)
    protocol: str | None = None
    led_package: str | None = None
    road_type: str | None = None
    pole_height_m: float | None = Field(None, gt=0)
    pole_spacing_m: float | None = Field(None, gt=0)
    ambient_temperature_c: float | None = None


class CriterionOut(BaseModel):
    criterion: str
    label: str
    status: str  # valid / warning / blocking / not_verifiable
    detail: str


class AlternativeConfigurationOut(BaseModel):
    driver: ComponentRef | None
    module: ComponentRef
    lens: ComponentRef | None
    status: str
    overall_score: float
    scores: ScoresOut
    warnings: list[str]


class ConfiguratorResultResponse(BaseModel):
    """Reponse commune aux endpoints /validate et /recommend-missing."""

    selection_mode: str
    status: str
    is_compatible: bool
    needs_manual_validation: bool
    driver: ComponentRef | None
    module: ComponentRef | None
    lens: ComponentRef | None
    scores: ScoresOut | None
    validated_rules: list[str]
    warnings: list[str]
    blocking_reasons: list[str]
    criteria: list[CriterionOut]
    explanation: str
    suggestions: list[str] = []
    alternatives: list[AlternativeConfigurationOut] = []


class ValidateConfigurationRequest(BaseModel):
    selection_mode: str = Field("manual", pattern="^(manual|hybrid)$")
    driver_id: int | None = None
    module_id: int
    lens_id: int | None = None
    project_requirements: PartialRequirements = PartialRequirements()


class RecommendMissingRequest(BaseModel):
    driver_id: int | None = None
    module_id: int | None = None
    lens_id: int | None = None
    project_requirements: PartialRequirements = PartialRequirements()


class ConfiguratorOptionItem(BaseModel):
    """Une ligne de picker (module/driver/lentille) avec statut de compatibilite optionnel."""

    id: int
    external_ref: str
    manufacturer: str
    reference: str
    product_family: str | None = None
    key_specs: dict
    status: str | None = None  # None si aucun contexte de comparaison n'a pu etre calcule
    is_active: bool


class ConfiguratorOptionsResponse(BaseModel):
    selection_modes: list[dict]
    protocols: list[str]
    manufacturers: dict[str, list[str]]
    counts: dict[str, int]


class SaveConfigurationRequest(BaseModel):
    project_id: int | None = None
    selection_mode: str = Field(..., pattern="^(automatic|manual|hybrid)$")
    driver_id: int | None = None
    module_id: int
    lens_id: int | None = None
    status: str
    overall_score: float | None = None
    validated_rules: list[str] = []
    blocking_reasons: list[str] = []
    warnings: list[str] = []
    user_comment: str | None = None
    is_favorite: bool = False


class SavedConfigurationRead(BaseModel):
    id: int
    project_id: int | None
    selection_mode: str
    driver: ComponentRef | None
    module: ComponentRef
    lens: ComponentRef | None
    status: str
    overall_score: float | None
    validated_rules: list[str]
    blocking_reasons: list[str]
    warnings: list[str]
    user_comment: str | None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime
    validated_at: datetime | None

    model_config = {"from_attributes": False}
