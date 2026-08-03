from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, TraceabilityMixin


class LedModule(TraceabilityMixin, TimestampMixin, Base):
    """Module LED. Colonnes issues de 'led_modules_cleaned' de LED_Modules_Database_Cleaned.xlsx."""

    __tablename__ = "led_modules"
    __table_args__ = {"schema": "catalog"}

    id: Mapped[int] = mapped_column(primary_key=True)
    external_ref: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # ex: MOD-0001

    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("catalog.manufacturers.id"), nullable=False)
    manufacturer: Mapped["Manufacturer"] = relationship()  # noqa: F821

    reference: Mapped[str] = mapped_column(String(255), nullable=False)
    product_family: Mapped[str | None] = mapped_column(String(255))
    product_name: Mapped[str | None] = mapped_column(String(255))
    module_type: Mapped[str | None] = mapped_column(String(50))
    application: Mapped[str | None] = mapped_column(String(100))
    module_status: Mapped[str | None] = mapped_column(String(30))

    # --- LED source ---
    led_manufacturer: Mapped[str | None] = mapped_column(String(150))
    led_reference: Mapped[str | None] = mapped_column(String(255))
    led_package: Mapped[str | None] = mapped_column(String(30))
    led_power_category: Mapped[str | None] = mapped_column(String(30))
    led_quantity: Mapped[int | None] = mapped_column(Integer)

    # --- Configuration electrique ---
    series_parallel_configuration: Mapped[str | None] = mapped_column(String(50))
    electrical_configuration: Mapped[str | None] = mapped_column(String(30))
    constant_current_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    constant_voltage_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Electrique (utilise par le moteur de compatibilite) ---
    input_voltage_nominal_v: Mapped[float | None] = mapped_column()
    current_nominal_ma: Mapped[float | None] = mapped_column()
    power_nominal_w: Mapped[float | None] = mapped_column()

    # --- Photometrie ---
    luminous_flux_nominal_lm: Mapped[float] = mapped_column(nullable=False)
    luminous_efficacy_nominal_lm_w: Mapped[float | None] = mapped_column()
    cct_nominal_k: Mapped[int] = mapped_column(Integer, nullable=False)
    cct_options: Mapped[str | None] = mapped_column(String(100))  # liste CCT dispo, ex: "3000,4000,5000"
    cri_min: Mapped[int | None] = mapped_column(Integer)

    # --- Thermique ---
    tc_point_temperature_max_c: Mapped[float | None] = mapped_column()

    # --- PCB / mecanique ---
    pcb_type: Mapped[str | None] = mapped_column(String(30))
    pcb_base_material: Mapped[str | None] = mapped_column(String(50))
    length_mm: Mapped[float | None] = mapped_column()
    width_mm: Mapped[float | None] = mapped_column()
    height_mm: Mapped[float | None] = mapped_column()

    # --- Fiabilite ---
    lifetime_hours: Mapped[int | None] = mapped_column(Integer)
    lumen_maintenance_standard: Mapped[str | None] = mapped_column(String(30))
    l70_hours: Mapped[float | None] = mapped_column()
    reliability_notes: Mapped[str | None] = mapped_column(Text)

    # --- Certifications ---
    ce_certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enec_certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ul_certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rohs_compliant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    certifications: Mapped[str | None] = mapped_column(Text)
    standards: Mapped[str | None] = mapped_column(Text)
    ip_rating: Mapped[str | None] = mapped_column(String(10))
    ik_rating: Mapped[str | None] = mapped_column(String(10))

    # --- Compatibilite driver declaree par le fabricant (utilisee par R-003 module_compatibility_rules) ---
    driver_compatibility_notes: Mapped[str | None] = mapped_column(Text)
    driver_compat_current_min_ma: Mapped[float | None] = mapped_column()
    driver_compat_current_max_ma: Mapped[float | None] = mapped_column()

    # --- Densites (indicateurs qualite optique/thermique) ---
    surface_area_mm2: Mapped[float | None] = mapped_column()
    luminous_density_lm_mm2: Mapped[float | None] = mapped_column()
    power_density_w_mm2: Mapped[float | None] = mapped_column()

    benchmark_score: Mapped[float | None] = mapped_column()
    benchmark_rank: Mapped[int | None] = mapped_column(Integer)

    datasheet_url: Mapped[str | None] = mapped_column(Text)

    validation_status: Mapped[str | None] = mapped_column(String(50))
    validation_message: Mapped[str | None] = mapped_column(Text)
