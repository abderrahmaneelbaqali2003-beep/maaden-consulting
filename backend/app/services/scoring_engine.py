"""Moteur de scoring (section 12.F). Score calcule uniquement pour les configurations
ayant deja passe toutes les regles bloquantes applicables.

Repartition sur 100 points (section 12) :
    - Compatibilite electrique (driver <-> module)      : 35 pts
    - Adequation flux + CCT                              : 25 pts
    - Compatibilite mecanique/optique (module <-> lentille) : 20 pts
    - Compatibilite thermique                            : 10 pts
    - Qualite et completude des donnees                  : 10 pts

Formules documentees ci-dessous, chaque sous-score est un compromis simple et
explicable plutot qu'une optimisation complexe, conformement au principe "le moteur
ne doit jamais inventer" : en absence de donnee, un score neutre (mi-echelle) est
attribue plutot qu'un score parfait ou nul, et le doute est toujours signale via un
avertissement genere ailleurs dans le pipeline (matchers), pas ici.
"""

from dataclasses import dataclass

from app.core.config import Settings
from app.database.models import Driver, LedModule, Lens, ProjectRequirement


@dataclass
class ScoreBreakdown:
    electrical: float
    photometric: float
    mechanical: float
    thermal: float
    data_quality: float

    @property
    def overall(self) -> float:
        return round(self.electrical + self.photometric + self.mechanical + self.thermal + self.data_quality, 1)


def _score_electrical(driver: Driver | None, module: LedModule, settings: Settings) -> float:
    """35 pts : 20 pts marge de puissance + 15 pts centrage de la tension dans la plage driver.
    0 pt si aucun driver n'est encore selectionne (selection manuelle partielle)."""
    if driver is None:
        return 0.0

    power_score = 10.0  # valeur neutre par defaut si non calculable
    if module.power_nominal_w:
        margin_ratio = driver.output_power_max_w / module.power_nominal_w - 1
        min_margin = settings.safety_factor - 1
        # 0 pts au minimum requis, 20 pts a partir de 30% de marge
        power_score = 20 * max(0.0, min(1.0, (margin_ratio - min_margin) / (0.30 - min_margin))) if 0.30 > min_margin else 20.0

    voltage_score = 7.5  # valeur neutre par defaut
    if module.input_voltage_nominal_v is not None:
        v_min, v_max = driver.output_voltage_min_v, driver.output_voltage_max_v
        half_range = (v_max - v_min) / 2
        if half_range > 0:
            distance_from_center = abs(module.input_voltage_nominal_v - (v_min + v_max) / 2)
            voltage_score = 15 * max(0.0, 1 - distance_from_center / half_range)
        else:
            voltage_score = 15.0

    return round(power_score + voltage_score, 2)


def _score_photometric(module: LedModule, requirement: ProjectRequirement, settings: Settings) -> float:
    """25 pts : 15 pts precision du flux + 10 pts correspondance CCT.
    Score neutre (moitie des points) pour chaque partie dont le besoin n'est pas renseigne
    (selection manuelle sans besoins projet remplis)."""
    if requirement.required_flux_lm is not None:
        flux_ratio = module.luminous_flux_nominal_lm / requirement.required_flux_lm
        if flux_ratio >= 1:
            denom = max(settings.flux_tolerance_max - 1, 0.0001)
        else:
            denom = max(1 - settings.flux_tolerance_min, 0.0001)
        flux_score = 15 * max(0.0, 1 - abs(flux_ratio - 1) / denom)
    else:
        flux_score = 7.5

    if requirement.required_cct_k is not None:
        cct_score = 10.0 if module.cct_nominal_k == requirement.required_cct_k else 6.0
    else:
        cct_score = 5.0

    return round(flux_score + cct_score, 2)


def _score_mechanical(lens: Lens | None, warnings_count: int) -> float:
    """20 pts : part depuis 20 et deduit 3 pts par avertissement mecanique/optique/photometrique
    (compatibilite non totalement verifiable), plancher 0. Aucune lentille trouvee = 0."""
    if lens is None:
        return 0.0
    return round(max(0.0, 20 - 3 * warnings_count), 2)


def _score_thermal(
    driver: Driver | None, module: LedModule, lens: Lens | None, requirement: ProjectRequirement
) -> float:
    """10 pts : si temperature ambiante non fournie, score neutre (5/10, non verifiable).
    Sinon, marge = distance a la limite la plus contraignante parmi driver/lentille."""
    if requirement.ambient_temperature_c is None:
        return 5.0

    driver_limit = driver.ambient_temperature_max_c if driver is not None else None
    limits = [v for v in [driver_limit, lens.operating_temperature_max_c if lens else None] if v is not None]
    if not limits:
        return 5.0

    tightest_limit = min(limits)
    margin = tightest_limit - requirement.ambient_temperature_c
    # 10 pts si marge >= 15 C, 0 pt si marge <= 0 (les cas <0 sont deja elimines par les regles bloquantes)
    return round(10 * max(0.0, min(1.0, margin / 15)), 2)


def _score_data_quality(driver: Driver | None, module: LedModule, lens: Lens | None) -> float:
    """10 pts : moyenne des scores qualite (0-100) issus du nettoyage source, ramenee sur 10."""
    scores = [s for s in [driver.data_quality_score if driver else None, module.data_quality_score] if s is not None]
    if lens is not None and lens.data_quality_score is not None:
        scores.append(lens.data_quality_score)
    if not scores:
        return 5.0
    return round((sum(scores) / len(scores)) / 10, 2)


def compute_scores(
    driver: Driver | None,
    module: LedModule,
    lens: Lens | None,
    requirement: ProjectRequirement,
    settings: Settings,
    mechanical_warnings_count: int,
) -> ScoreBreakdown:
    return ScoreBreakdown(
        electrical=_score_electrical(driver, module, settings),
        photometric=_score_photometric(module, requirement, settings),
        mechanical=_score_mechanical(lens, mechanical_warnings_count),
        thermal=_score_thermal(driver, module, lens, requirement),
        data_quality=_score_data_quality(driver, module, lens),
    )
