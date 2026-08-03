from sqlalchemy import Boolean, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class CompatibilityRule(TimestampMixin, Base):
    """Regle de compatibilite deterministe. Chargee depuis les feuilles
    driver_compatibility_rules / module_compatibility_rules / lens_compatibility_rules
    des fichiers Excel sources (import_service), avec possibilite d'ajustement manuel ulterieur.
    """

    __tablename__ = "compatibility_rules"
    __table_args__ = {"schema": "catalog"}

    __table_args__ = (
        UniqueConstraint("entity_type", "external_rule_id", name="uq_compatibility_rule_entity_ref"),
        {"schema": "catalog"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_rule_id: Mapped[str] = mapped_column(String(20), nullable=False)  # ex: R-001 (par entity_type)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # driver / module / lens
    rule_category: Mapped[str | None] = mapped_column(String(30))
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[str | None] = mapped_column(String(20))
    requirement_field: Mapped[str] = mapped_column(String(150), nullable=False)
    tolerance_value: Mapped[float | None] = mapped_column()
    tolerance_unit: Mapped[str | None] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # blocking / warning
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class DriverModuleCompatibility(TimestampMixin, Base):
    """Cache du resultat de compatibilite driver <-> module calcule par le moteur.

    Alimente par le moteur de recommandation (services/driver_module_matcher.py) pour eviter
    de recalculer une paire deja evaluee. Pas une source de verite : recalculable a tout moment.
    """

    __tablename__ = "driver_module_compatibility"
    __table_args__ = (
        UniqueConstraint("driver_id", "module_id", name="uq_driver_module_pair"),
        {"schema": "catalog"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("catalog.drivers.id"), nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("catalog.led_modules.id"), nullable=False)
    is_compatible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    electrical_score: Mapped[float | None] = mapped_column()
    validated_rules: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    blocking_reasons: Mapped[list] = mapped_column(JSON, default=list)


class ModuleLensCompatibility(TimestampMixin, Base):
    """Cache du resultat de compatibilite module <-> lentille calcule par le moteur."""

    __tablename__ = "module_lens_compatibility"
    __table_args__ = (
        UniqueConstraint("module_id", "lens_id", name="uq_module_lens_pair"),
        {"schema": "catalog"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("catalog.led_modules.id"), nullable=False)
    lens_id: Mapped[int] = mapped_column(ForeignKey("catalog.lenses.id"), nullable=False)
    is_compatible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    mechanical_score: Mapped[float | None] = mapped_column()
    validated_rules: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    blocking_reasons: Mapped[list] = mapped_column(JSON, default=list)
