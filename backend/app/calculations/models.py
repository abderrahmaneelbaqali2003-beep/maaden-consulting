"""Modeles structures du calculateur technique.

Chaque grandeur calculee est enveloppee dans un `CalculationValue` : une
donnee d'entree manquante ne produit jamais une valeur a zero silencieuse,
mais `status="not_calculable"` + un `warning` explicite. Les estimations
(non normatives, ex: eclairement moyen) portent `is_estimate=True` et un
avertissement rappelant qu'elles ne remplacent pas une simulation DIALux.
"""

from typing import Literal

from pydantic import BaseModel, Field

CalculationStatus = Literal["calculated", "estimate", "not_calculable", "to_validate"]


class CalculationValue(BaseModel):
    key: str
    label: str
    value: float | int | None = None
    unit: str | None = None
    status: CalculationStatus
    formula: str | None = None
    inputs: dict[str, float | int | str | None] = Field(default_factory=dict)
    is_estimate: bool = False
    warning: str | None = None


class DimmingProfileEntry(BaseModel):
    """Un palier d'un profil de gradation journalier (V1 : estimation proportionnelle)."""

    duration_hours: float = Field(..., gt=0, le=24)
    level_percent: float = Field(..., ge=0, le=100)


class CalculationInput(BaseModel):
    """Superset optionnel : donnees projet + donnees produit (si deja connues).

    Aucun champ n'est obligatoire : `CalculationService` calcule seulement les
    grandeurs dont les entrees necessaires sont presentes.
    """

    # --- Geometrie routiere ---
    road_width_m: float | None = None
    road_length_m: float | None = None
    pole_height_m: float | None = None
    pole_spacing_m: float | None = None
    layout_type: Literal["unilateral", "opposite", "staggered", "central"] | None = None

    # --- Eclairage / photometrie ---
    required_flux_lm: float | None = None
    utilization_factor: float | None = None
    maintenance_factor: float | None = None
    illuminance_min_lux: float | None = None
    illuminance_avg_lux: float | None = None

    # --- Electrique (besoin projet) ---
    module_voltage_v: float | None = None
    module_current_ma: float | None = None
    module_power_nominal_w: float | None = None  # valeur fabricant si connue (comparaison uniquement)

    # --- Donnees produit (si driver/module/lentille deja selectionnes) ---
    driver_power_max_w: float | None = None
    driver_max_temperature_c: float | None = None
    lens_max_temperature_c: float | None = None

    # --- Environnement ---
    ambient_temperature_c: float | None = None

    # --- Energie ---
    operating_hours_per_year: float | None = None
    energy_price_per_kwh: float | None = None
    reference_energy_kwh: float | None = None
    dimming_profile: list[DimmingProfileEntry] | None = None


class ElectricalCalculationResult(BaseModel):
    module_power_w: CalculationValue
    module_power_consistency_percent: CalculationValue
    driver_required_power_w: CalculationValue
    driver_loading_percent: CalculationValue
    driver_power_margin_percent: CalculationValue
    luminous_efficacy_lm_w: CalculationValue


class GeometryCalculationResult(BaseModel):
    spacing_height_ratio: CalculationValue
    road_segment_area_m2: CalculationValue
    estimated_luminaire_count: CalculationValue


class ThermalCalculationResult(BaseModel):
    driver_thermal_margin_c: CalculationValue
    lens_thermal_margin_c: CalculationValue
    tightest_thermal_margin_c: CalculationValue


class EnergyCalculationResult(BaseModel):
    total_installed_power_kw: CalculationValue
    annual_energy_kwh: CalculationValue
    annual_energy_with_dimming_kwh: CalculationValue
    energy_saving_percent: CalculationValue
    energy_saved_kwh_year: CalculationValue
    annual_energy_cost: CalculationValue


class PhotometricEstimateResult(BaseModel):
    estimated_average_illuminance_lux: CalculationValue
    uniformity_u0: CalculationValue


class CalculationResult(BaseModel):
    electrical: ElectricalCalculationResult
    geometry: GeometryCalculationResult
    thermal: ThermalCalculationResult
    energy: EnergyCalculationResult
    photometric: PhotometricEstimateResult
    warnings: list[str] = Field(default_factory=list)
