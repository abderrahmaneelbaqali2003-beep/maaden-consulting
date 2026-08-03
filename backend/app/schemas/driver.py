from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ManufacturerRead


class DriverBase(BaseModel):
    reference: str = Field(..., min_length=1, max_length=255)
    product_family: str | None = None
    product_name: str | None = None
    driver_type: str | None = None
    application: str | None = None

    input_voltage_nominal_v: float | None = Field(None, ge=0)

    output_type: str | None = None
    output_voltage_min_v: float = Field(..., ge=0)
    output_voltage_nominal_v: float | None = Field(None, ge=0)
    output_voltage_max_v: float = Field(..., ge=0)
    output_current_min_ma: float | None = Field(None, ge=0)
    output_current_nominal_ma: float | None = Field(None, ge=0)
    output_current_max_ma: float | None = Field(None, ge=0)
    output_power_nominal_w: float | None = Field(None, ge=0)
    output_power_max_w: float = Field(..., ge=0)

    efficiency_percent: float | None = Field(None, ge=0, le=100)
    power_factor: float | None = Field(None, ge=0, le=1)
    thd_percent: float | None = Field(None, ge=0)

    dimmable: bool = False
    dimming_0_10v: bool = False
    dimming_1_10v: bool = False
    dali_2: bool = False
    d4i: bool = False
    pwm_dimming: bool = False
    resistance_dimming: bool = False

    ambient_temperature_min_c: float | None = None
    ambient_temperature_max_c: float | None = None
    tc_max_c: float | None = None

    ip_rating: str | None = None
    electrical_class: str | None = None
    surge_line_to_line_kv: float | None = Field(None, ge=0)
    surge_line_to_earth_kv: float | None = Field(None, ge=0)
    warranty_years: int | None = Field(None, ge=0)
    ce_certified: bool = False
    enec_certified: bool = False
    ul_certified: bool = False
    rohs_compliant: bool = False
    certifications: str | None = None
    standards: str | None = None

    outdoor_direct: str | None = None
    outdoor_robustness_score_10: float | None = Field(None, ge=0, le=10)
    smart_lighting_level: int | None = None
    benchmark_score: float | None = None
    benchmark_rank: int | None = None

    datasheet_url: str | None = None
    notes: str | None = None


class DriverCreate(DriverBase):
    external_ref: str = Field(..., min_length=1, max_length=20)
    manufacturer: str = Field(..., min_length=1, description="Nom du fabricant (cree automatiquement si nouveau)")


class DriverUpdate(BaseModel):
    """Tous les champs sont optionnels : seuls ceux fournis sont modifies."""

    reference: str | None = None
    manufacturer: str | None = None
    product_family: str | None = None
    product_name: str | None = None
    driver_type: str | None = None
    application: str | None = None
    input_voltage_nominal_v: float | None = None
    output_type: str | None = None
    output_voltage_min_v: float | None = None
    output_voltage_nominal_v: float | None = None
    output_voltage_max_v: float | None = None
    output_current_min_ma: float | None = None
    output_current_nominal_ma: float | None = None
    output_current_max_ma: float | None = None
    output_power_nominal_w: float | None = None
    output_power_max_w: float | None = None
    efficiency_percent: float | None = None
    power_factor: float | None = None
    thd_percent: float | None = None
    dimmable: bool | None = None
    dimming_0_10v: bool | None = None
    dimming_1_10v: bool | None = None
    dali_2: bool | None = None
    d4i: bool | None = None
    pwm_dimming: bool | None = None
    resistance_dimming: bool | None = None
    ambient_temperature_min_c: float | None = None
    ambient_temperature_max_c: float | None = None
    tc_max_c: float | None = None
    ip_rating: str | None = None
    electrical_class: str | None = None
    warranty_years: int | None = None
    ce_certified: bool | None = None
    enec_certified: bool | None = None
    ul_certified: bool | None = None
    rohs_compliant: bool | None = None
    certifications: str | None = None
    standards: str | None = None
    datasheet_url: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class DriverRead(DriverBase):
    id: int
    external_ref: str
    manufacturer: ManufacturerRead
    source_name: str | None = None
    data_quality_score: float | None = None
    data_quality_level: str | None = None
    needs_manual_validation: bool
    is_active: bool
    validation_status: str | None = None
    validation_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
