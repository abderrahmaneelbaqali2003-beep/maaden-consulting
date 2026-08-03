from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ManufacturerRead


class LensBase(BaseModel):
    reference: str = Field(..., min_length=1, max_length=255)
    product_family: str | None = None
    product_name: str | None = None
    lens_type: str | None = None
    application: str | None = None
    product_status: str | None = None
    catalog_level: str | None = None

    compatible_led_package: str | None = None
    compatible_led_power_category: str | None = None
    compatibility_status: str | None = None
    compatibility_source: str | None = None
    compatibility_notes: str | None = None
    compat_2835: bool | None = None
    compat_3030: bool | None = None
    compat_3535: bool | None = None
    compat_5050: bool | None = None
    compat_7070: bool | None = None
    compat_csp: bool | None = None
    compat_cob: bool | None = None

    optical_cells_quantity: int | None = Field(None, ge=0)
    rows_count: int | None = Field(None, ge=0)
    columns_count: int | None = Field(None, ge=0)
    configuration_description: str | None = None
    lens_pitch_x_mm: float | None = Field(None, ge=0)
    lens_pitch_y_mm: float | None = Field(None, ge=0)

    iesna_distribution_type: str | None = None
    beam_distribution_name: str | None = None
    beam_angle_horizontal_deg: float | None = Field(None, ge=0, le=360)
    asymmetry_type: str | None = None
    photometric_classification: str | None = None
    photometric_notes: str | None = None
    ies_file_available: bool = False
    ldt_file_available: bool = False

    road_application: str | None = None
    road_application_notes: str | None = None
    app_highway: bool | None = None
    app_national_road: bool | None = None
    app_urban_road: bool | None = None

    optical_material: str | None = None
    uv_resistant: bool | None = None
    operating_temperature_max_c: float | None = None

    length_mm: float | None = Field(None, ge=0)
    width_mm: float | None = Field(None, ge=0)
    height_mm: float | None = Field(None, ge=0)
    diameter_mm: float | None = Field(None, ge=0)
    mounting_hole_pitch_x_mm: float | None = None
    mounting_hole_pitch_y_mm: float | None = None
    compatible_led_height_mm: float | None = None
    gasket_required: bool | None = None
    outdoor_use: bool | None = None

    standards: str | None = None
    compliance_status: str | None = None
    product_url: str | None = None
    distribution_detail: str | None = None
    distribution_status_raw: str | None = None
    notes: str | None = None


class LensCreate(LensBase):
    external_ref: str = Field(..., min_length=1, max_length=20)
    manufacturer: str = Field(..., min_length=1)


class LensUpdate(BaseModel):
    reference: str | None = None
    manufacturer: str | None = None
    compatible_led_package: str | None = None
    optical_cells_quantity: int | None = None
    rows_count: int | None = None
    columns_count: int | None = None
    lens_pitch_x_mm: float | None = None
    lens_pitch_y_mm: float | None = None
    iesna_distribution_type: str | None = None
    ies_file_available: bool | None = None
    ldt_file_available: bool | None = None
    length_mm: float | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    notes: str | None = None
    is_active: bool | None = None


class LensRead(LensBase):
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
