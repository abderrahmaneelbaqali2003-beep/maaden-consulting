from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, TraceabilityMixin


class Lens(TraceabilityMixin, TimestampMixin, Base):
    """Lentille optique. Colonnes issues de 'lenses_cleaned' de LED_Lenses_Database_Cleaned.xlsx.

    Attention : la base source a une qualite de donnees tres faible (score moyen 31.9/100,
    aucun fichier IES/LDT disponible). Les colonnes photometriques et de fichiers IES/LDT
    sont conservees car elles sont indispensables au moteur (statuts manual_validation_required /
    compatible_with_warning), meme si actuellement vides pour la quasi-totalite des lignes.
    """

    __tablename__ = "lenses"
    __table_args__ = {"schema": "catalog"}

    id: Mapped[int] = mapped_column(primary_key=True)
    external_ref: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # ex: LEN-0001

    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("catalog.manufacturers.id"), nullable=False)
    manufacturer: Mapped["Manufacturer"] = relationship()  # noqa: F821

    reference: Mapped[str] = mapped_column(String(255), nullable=False)
    product_family: Mapped[str | None] = mapped_column(String(255))
    product_name: Mapped[str | None] = mapped_column(String(255))
    lens_type: Mapped[str | None] = mapped_column(String(50))
    application: Mapped[str | None] = mapped_column(String(100))
    product_status: Mapped[str | None] = mapped_column(String(30))
    catalog_level: Mapped[str | None] = mapped_column(String(30))  # Reference / Famille / Sous-famille (niveau de granularite de la ligne source)

    # --- Compatibilite LED declaree (utilisee par les regles R-001 a R-003 lens_compatibility_rules) ---
    compatible_led_package: Mapped[str | None] = mapped_column(String(150))  # liste ex: "2835,3030,3535"
    compatible_led_power_category: Mapped[str | None] = mapped_column(String(30))
    compatibility_status: Mapped[str | None] = mapped_column(String(30))  # probable / unverified / confirmed...
    compatibility_source: Mapped[str | None] = mapped_column(String(100))
    compatibility_notes: Mapped[str | None] = mapped_column(Text)
    compat_2835: Mapped[bool | None] = mapped_column(Boolean)
    compat_3030: Mapped[bool | None] = mapped_column(Boolean)
    compat_3535: Mapped[bool | None] = mapped_column(Boolean)
    compat_5050: Mapped[bool | None] = mapped_column(Boolean)
    compat_7070: Mapped[bool | None] = mapped_column(Boolean)
    compat_csp: Mapped[bool | None] = mapped_column(Boolean)
    compat_cob: Mapped[bool | None] = mapped_column(Boolean)

    # --- Layout optique (R-003/R-004/R-005/R-006) ---
    optical_cells_quantity: Mapped[int | None] = mapped_column(Integer)
    rows_count: Mapped[int | None] = mapped_column(Integer)
    columns_count: Mapped[int | None] = mapped_column(Integer)
    configuration_description: Mapped[str | None] = mapped_column(String(255))
    lens_pitch_x_mm: Mapped[float | None] = mapped_column()
    lens_pitch_y_mm: Mapped[float | None] = mapped_column()

    # --- Photometrie (R-009/R-010/R-011) ---
    iesna_distribution_type: Mapped[str | None] = mapped_column(String(30))
    beam_distribution_name: Mapped[str | None] = mapped_column(String(150))
    beam_angle_horizontal_deg: Mapped[float | None] = mapped_column()
    asymmetry_type: Mapped[str | None] = mapped_column(String(30))
    photometric_classification: Mapped[str | None] = mapped_column(String(30))  # estimated / confirmed
    photometric_notes: Mapped[str | None] = mapped_column(Text)
    ies_file_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ldt_file_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Application routiere (extension future : donnees routieres avancees) ---
    road_application: Mapped[str | None] = mapped_column(String(50))
    road_application_notes: Mapped[str | None] = mapped_column(Text)
    app_highway: Mapped[bool | None] = mapped_column(Boolean)
    app_national_road: Mapped[bool | None] = mapped_column(Boolean)
    app_urban_road: Mapped[bool | None] = mapped_column(Boolean)

    # --- Materiaux / environnement (R-012/R-013) ---
    optical_material: Mapped[str | None] = mapped_column(String(30))
    uv_resistant: Mapped[bool | None] = mapped_column(Boolean)
    operating_temperature_max_c: Mapped[float | None] = mapped_column()

    # --- Mecanique (R-007/R-008) ---
    length_mm: Mapped[float | None] = mapped_column()
    width_mm: Mapped[float | None] = mapped_column()
    height_mm: Mapped[float | None] = mapped_column()
    diameter_mm: Mapped[float | None] = mapped_column()
    mounting_hole_pitch_x_mm: Mapped[float | None] = mapped_column()
    mounting_hole_pitch_y_mm: Mapped[float | None] = mapped_column()
    compatible_led_height_mm: Mapped[float | None] = mapped_column()
    gasket_required: Mapped[bool | None] = mapped_column(Boolean)
    outdoor_use: Mapped[bool | None] = mapped_column(Boolean)

    standards: Mapped[str | None] = mapped_column(Text)
    compliance_status: Mapped[str | None] = mapped_column(String(30))
    product_url: Mapped[str | None] = mapped_column(Text)

    distribution_detail: Mapped[str | None] = mapped_column(String(255))
    distribution_status_raw: Mapped[str | None] = mapped_column(String(100))

    validation_status: Mapped[str | None] = mapped_column(String(50))
    validation_message: Mapped[str | None] = mapped_column(Text)
