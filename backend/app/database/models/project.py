from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class ProjectRequirement(TimestampMixin, Base):
    """Un jeu de besoins saisi via le formulaire 'Nouveau calcul' (section 11 du cahier des charges)."""

    __tablename__ = "project_requirements"
    __table_args__ = {"schema": "consulting"}

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("consulting.projects.id"))

    # --- Criteres obligatoires ---
    required_flux_lm: Mapped[float] = mapped_column(nullable=False)
    max_power_w: Mapped[float] = mapped_column(nullable=False)
    required_cct_k: Mapped[int] = mapped_column(Integer, nullable=False)
    voltage_nominal_v: Mapped[float] = mapped_column(nullable=False)
    current_nominal_ma: Mapped[float] = mapped_column(nullable=False)

    # --- Criteres optionnels ---
    protocol: Mapped[str | None] = mapped_column(String(20))  # DALI / DALI-2 / D4i / 0-10V / 1-10V
    led_package: Mapped[str | None] = mapped_column(String(30))
    road_type: Mapped[str | None] = mapped_column(String(50))
    pole_height_m: Mapped[float | None] = mapped_column()
    pole_spacing_m: Mapped[float | None] = mapped_column()
    ambient_temperature_c: Mapped[float | None] = mapped_column()
