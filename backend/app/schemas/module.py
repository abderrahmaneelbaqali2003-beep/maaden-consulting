from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ManufacturerRead


class ModuleBase(BaseModel):
    reference: str = Field(..., min_length=1, max_length=255)
    product_family: str | None = None
    product_name: str | None = None
    module_type: str | None = None
    application: str | None = None
    module_status: str | None = None

    led_manufacturer: str | None = None
    led_reference: str | None = None
    led_package: str | None = None
    led_power_category: str | None = None
    led_quantity: int | None = Field(None, ge=0)

    series_parallel_configuration: str | None = None
    electrical_configuration: str | None = None
    constant_current_required: bool = False
    constant_voltage_required: bool = False

    input_voltage_nominal_v: float | None = Field(None, ge=0)
    current_nominal_ma: float | None = Field(None, ge=0)
    power_nominal_w: float | None = Field(None, ge=0)

    luminous_flux_nominal_lm: float = Field(..., gt=0)
    luminous_efficacy_nominal_lm_w: float | None = Field(None, ge=0)
    cct_nominal_k: int = Field(..., gt=0)
    cct_options: str | None = None
    cri_min: int | None = Field(None, ge=0, le=100)

    tc_point_temperature_max_c: float | None = None

    pcb_type: str | None = None
    pcb_base_material: str | None = None
    length_mm: float | None = Field(None, ge=0)
    width_mm: float | None = Field(None, ge=0)
    height_mm: float | None = Field(None, ge=0)

    lifetime_hours: int | None = Field(None, ge=0)
    lumen_maintenance_standard: str | None = None
    l70_hours: float | None = None
    reliability_notes: str | None = None

    ce_certified: bool = False
    enec_certified: bool = False
    ul_certified: bool = False
    rohs_compliant: bool = False
    certifications: str | None = None
    standards: str | None = None
    ip_rating: str | None = None
    ik_rating: str | None = None

    driver_compatibility_notes: str | None = None
    driver_compat_current_min_ma: float | None = None
    driver_compat_current_max_ma: float | None = None

    benchmark_score: float | None = None
    benchmark_rank: int | None = None
    datasheet_url: str | None = None
    notes: str | None = None


class ModuleCreate(ModuleBase):
    external_ref: str = Field(..., min_length=1, max_length=20)
    manufacturer: str = Field(..., min_length=1)


class ModuleUpdate(BaseModel):
    reference: str | None = None
    manufacturer: str | None = None
    product_family: str | None = None
    product_name: str | None = None
    led_package: str | None = None
    led_quantity: int | None = None
    input_voltage_nominal_v: float | None = None
    current_nominal_ma: float | None = None
    power_nominal_w: float | None = None
    luminous_flux_nominal_lm: float | None = None
    luminous_efficacy_nominal_lm_w: float | None = None
    cct_nominal_k: int | None = None
    cct_options: str | None = None
    cri_min: int | None = None
    length_mm: float | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    ce_certified: bool | None = None
    rohs_compliant: bool | None = None
    datasheet_url: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class ModuleRead(ModuleBase):
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
