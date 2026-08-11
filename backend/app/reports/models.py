"""Modeles de donnees du rapport PDF : une structure intermediaire, en lecture seule,
assemblee par `ReportService` puis mise en page par `PdfGenerator`. Aucun de ces
modeles n'est jamais ecrit en base ; ils ne font que refleter des donnees deja
persistees (`RecommendationResult`, `ProjectRequirement`, `Driver`, `LedModule`,
`Lens`, `RecommendationEvidence`, `ExpertValidation`) + le `CalculationResult`
recalcule (calcul pur, jamais re-implemente ici).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.calculations.models import CalculationResult


class ReportProjectData(BaseModel):
    road_type: str | None = None
    road_width_m: float | None = None
    road_length_m: float | None = None
    pole_height_m: float | None = None
    pole_spacing_m: float | None = None
    layout_type: str | None = None
    required_flux_lm: float
    required_cct_k: int
    max_power_w: float
    voltage_nominal_v: float
    current_nominal_ma: float
    protocol: str | None = None
    led_package: str | None = None
    ambient_temperature_c: float | None = None


class ReportDriverData(BaseModel):
    manufacturer: str
    reference: str
    product_family: str | None = None
    output_power_max_w: float | None = None
    output_voltage_min_v: float | None = None
    output_voltage_max_v: float | None = None
    output_current_min_ma: float | None = None
    output_current_max_ma: float | None = None
    efficiency_percent: float | None = None
    dimmable: bool | None = None
    dali_2: bool | None = None
    d4i: bool | None = None
    protocols: list[str] = []
    ip_rating: str | None = None
    ce_certified: bool | None = None
    enec_certified: bool | None = None
    ul_certified: bool | None = None
    rohs_compliant: bool | None = None
    certifications: str | None = None


class ReportModuleData(BaseModel):
    manufacturer: str
    reference: str
    product_family: str | None = None
    led_package: str | None = None
    led_quantity: int | None = None
    input_voltage_nominal_v: float | None = None
    current_nominal_ma: float | None = None
    power_nominal_w: float | None = None
    luminous_flux_nominal_lm: float
    luminous_efficacy_nominal_lm_w: float | None = None
    cct_nominal_k: int
    cri_min: int | None = None
    lifetime_hours: int | None = None
    ce_certified: bool | None = None
    enec_certified: bool | None = None
    ul_certified: bool | None = None
    rohs_compliant: bool | None = None
    ip_rating: str | None = None
    certifications: str | None = None


class ReportLensData(BaseModel):
    manufacturer: str
    reference: str
    compatible_led_package: str | None = None
    optical_cells_quantity: int | None = None
    rows_count: int | None = None
    columns_count: int | None = None
    lens_pitch_x_mm: float | None = None
    lens_pitch_y_mm: float | None = None
    iesna_distribution_type: str | None = None
    beam_angle_horizontal_deg: float | None = None
    ies_file_available: bool = False
    ldt_file_available: bool = False
    length_mm: float | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    diameter_mm: float | None = None
    operating_temperature_max_c: float | None = None


class ReportScoresData(BaseModel):
    overall: float
    electrical: float
    photometric: float
    mechanical: float
    thermal: float
    data_quality: float


class ReportEvidenceData(BaseModel):
    category: str
    document: str
    section: str | None = None
    page: int | None = None
    summary: str
    verification_status: str
    relevance_label: str


class ReportDocumentaryData(BaseModel):
    confidence: str
    evidence: list[ReportEvidenceData] = []
    missing_evidence: list[str] = []


class ReportValidationData(BaseModel):
    validator_name: str
    validated_at: datetime
    comment: str | None = None


class ReportData(BaseModel):
    reference: str
    generated_at: datetime
    template_version: str = "1.0"
    project_name: str | None = None
    project: ReportProjectData
    driver: ReportDriverData | None = None
    module: ReportModuleData
    lens: ReportLensData | None = None
    scores: ReportScoresData
    calculations: CalculationResult
    validated_rules: list[str] = []
    warnings: list[str] = []
    blocking_reasons: list[str] = []
    documentary: ReportDocumentaryData
    remaining_validations: list[str] = []
    conclusion: str
    validation: ReportValidationData
