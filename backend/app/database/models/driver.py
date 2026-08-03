from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, TraceabilityMixin


class Driver(TraceabilityMixin, TimestampMixin, Base):
    """Driver LED. Colonnes issues de la feuille 'drivers_cleaned' de LED_Drivers_Database_Cleaned.xlsx.

    Seules les colonnes reellement renseignees dans la source et/ou utilisees par le moteur
    de compatibilite (voir feuille 'driver_compatibility_rules') sont conservees.
    """

    __tablename__ = "drivers"
    __table_args__ = {"schema": "catalog"}

    id: Mapped[int] = mapped_column(primary_key=True)
    external_ref: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # ex: DRV-0001 (source)

    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("catalog.manufacturers.id"), nullable=False)
    manufacturer: Mapped["Manufacturer"] = relationship()  # noqa: F821

    reference: Mapped[str] = mapped_column(String(255), nullable=False)
    product_family: Mapped[str | None] = mapped_column(String(255))
    product_name: Mapped[str | None] = mapped_column(String(255))
    driver_type: Mapped[str | None] = mapped_column(String(50))
    application: Mapped[str | None] = mapped_column(String(100))

    # --- Electrique : entree ---
    input_voltage_nominal_v: Mapped[float | None] = mapped_column()

    # --- Electrique : sortie (utilise par le moteur de compatibilite) ---
    output_type: Mapped[str | None] = mapped_column(String(30))  # constant_current / constant_power
    output_voltage_min_v: Mapped[float] = mapped_column(nullable=False)
    output_voltage_nominal_v: Mapped[float | None] = mapped_column()
    output_voltage_max_v: Mapped[float] = mapped_column(nullable=False)
    output_current_min_ma: Mapped[float | None] = mapped_column()
    output_current_nominal_ma: Mapped[float | None] = mapped_column()
    output_current_max_ma: Mapped[float | None] = mapped_column()
    output_power_nominal_w: Mapped[float | None] = mapped_column()
    output_power_max_w: Mapped[float] = mapped_column(nullable=False)

    efficiency_percent: Mapped[float | None] = mapped_column()
    power_factor: Mapped[float | None] = mapped_column()
    thd_percent: Mapped[float | None] = mapped_column()

    # --- Protocoles / dimming (booleens fiables issus de la source) ---
    dimmable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dimming_0_10v: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dimming_1_10v: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dali_2: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    d4i: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pwm_dimming: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resistance_dimming: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Thermique ---
    ambient_temperature_min_c: Mapped[float | None] = mapped_column()
    ambient_temperature_max_c: Mapped[float | None] = mapped_column()
    tc_max_c: Mapped[float | None] = mapped_column()

    # --- Protection / mecanique / certifications ---
    ip_rating: Mapped[str | None] = mapped_column(String(10))
    electrical_class: Mapped[str | None] = mapped_column(String(30))
    surge_line_to_line_kv: Mapped[float | None] = mapped_column()
    surge_line_to_earth_kv: Mapped[float | None] = mapped_column()
    warranty_years: Mapped[int | None] = mapped_column(Integer)
    ce_certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enec_certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ul_certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rohs_compliant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    certifications: Mapped[str | None] = mapped_column(Text)
    standards: Mapped[str | None] = mapped_column(Text)

    # --- Robustesse outdoor / smart lighting (indicateurs benchmark source, utilises pour le scoring) ---
    outdoor_direct: Mapped[str | None] = mapped_column(String(50))
    outdoor_robustness_score_10: Mapped[float | None] = mapped_column()
    smart_lighting_level: Mapped[int | None] = mapped_column(Integer)
    benchmark_score: Mapped[float | None] = mapped_column()
    benchmark_rank: Mapped[int | None] = mapped_column(Integer)

    datasheet_url: Mapped[str | None] = mapped_column(Text)

    # --- Statut de validation issu du nettoyage source ---
    validation_status: Mapped[str | None] = mapped_column(String(50))
    validation_message: Mapped[str | None] = mapped_column(Text)
