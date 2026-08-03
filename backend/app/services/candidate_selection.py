"""Etape B du moteur (section 12) : selection des modules LED candidats.

Filtre strict (elimine directement, ne genere pas de configuration) sur : flux (avec
tolerance configurable), puissance maximale, CCT, package LED si demande. La tension et
le courant nominal du module sont compares au besoin avec une tolerance configurable,
mais un module dont le champ est absent n'est jamais elimine sur ce seul critere
(donnee manquante = non verifiable, pas incompatible).
"""

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import LedModule, ProjectRequirement


def _within_tolerance_percent(value: float, target: float, tolerance_percent: float) -> bool:
    if target == 0:
        return value == 0
    return abs(value - target) / target * 100 <= tolerance_percent


def select_candidate_modules(
    db: Session, requirement: ProjectRequirement, settings: Settings
) -> list[LedModule]:
    flux_min = requirement.required_flux_lm * settings.flux_tolerance_min
    flux_max = requirement.required_flux_lm * settings.flux_tolerance_max

    query = (
        db.query(LedModule)
        .filter(LedModule.is_active.is_(True))
        .filter(LedModule.luminous_flux_nominal_lm >= flux_min)
        .filter(LedModule.luminous_flux_nominal_lm <= flux_max)
    )

    candidates = []
    for module in query.all():
        if (
            module.power_nominal_w is not None
            and requirement.max_power_w is not None
            and module.power_nominal_w > requirement.max_power_w
        ):
            continue

        cct_ok = module.cct_nominal_k == requirement.required_cct_k
        if not cct_ok and module.cct_options:
            options = {opt.strip() for opt in str(module.cct_options).split(",") if opt.strip()}
            cct_ok = str(requirement.required_cct_k) in options
        if not cct_ok:
            continue

        if requirement.led_package and module.led_package and module.led_package != requirement.led_package:
            continue

        if (
            module.input_voltage_nominal_v is not None
            and requirement.voltage_nominal_v is not None
            and not _within_tolerance_percent(
                module.input_voltage_nominal_v, requirement.voltage_nominal_v, settings.module_voltage_tolerance_percent
            )
        ):
            continue

        if (
            module.current_nominal_ma is not None
            and requirement.current_nominal_ma is not None
            and not _within_tolerance_percent(
                module.current_nominal_ma, requirement.current_nominal_ma, settings.module_current_tolerance_percent
            )
        ):
            continue

        candidates.append(module)

    return candidates
