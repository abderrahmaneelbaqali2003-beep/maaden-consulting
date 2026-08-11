"""Grandeurs energetiques (section 3.J-N).

Ne jamais inventer un tarif electrique, des heures de fonctionnement ou une
consommation de reference : chaque fonction retourne `None` si une entree
necessaire est absente, laissant l'appelant (`service.py`) traduire cela en
`status="not_calculable"`.
"""

from app.calculations.models import DimmingProfileEntry


def calculate_total_installed_power_kw(
    number_of_luminaires: float | None, luminaire_power_w: float | None
) -> float | None:
    if number_of_luminaires is None or luminaire_power_w is None:
        return None
    return number_of_luminaires * luminaire_power_w / 1000


def calculate_annual_energy_kwh(
    number_of_luminaires: float | None, power_w: float | None, operating_hours_per_year: float | None
) -> float | None:
    """annual_energy_kwh = N x P(W) x heures / 1000."""
    if number_of_luminaires is None or power_w is None or operating_hours_per_year is None:
        return None
    return number_of_luminaires * power_w * operating_hours_per_year / 1000


def calculate_daily_energy_with_dimming_kwh(
    power_w: float | None,
    dimming_profile: list[DimmingProfileEntry] | None,
    number_of_luminaires: float | None = 1,
) -> float | None:
    """Estimation V1 proportionnelle au niveau de gradation renseigne uniquement :
    ne reproduit pas la courbe electrique reelle du driver (donnee fabricant absente).
    Profil invalide (duree totale <= 0 ou > 24h) -> None (jamais une estimation fausse)."""
    if power_w is None or not dimming_profile:
        return None
    total_hours = sum(entry.duration_hours for entry in dimming_profile)
    if total_hours <= 0 or total_hours > 24:
        return None
    total_wh = sum(power_w * (entry.level_percent / 100) * entry.duration_hours for entry in dimming_profile)
    return (number_of_luminaires or 1) * total_wh / 1000


def calculate_annual_energy_with_dimming_kwh(daily_energy_with_dimming_kwh: float | None) -> float | None:
    if daily_energy_with_dimming_kwh is None:
        return None
    return daily_energy_with_dimming_kwh * 365


def calculate_energy_saving_percent(
    proposed_energy_kwh: float | None, reference_energy_kwh: float | None
) -> float | None:
    if proposed_energy_kwh is None or reference_energy_kwh is None or reference_energy_kwh == 0:
        return None
    return (1 - proposed_energy_kwh / reference_energy_kwh) * 100


def calculate_energy_saved_kwh(proposed_energy_kwh: float | None, reference_energy_kwh: float | None) -> float | None:
    if proposed_energy_kwh is None or reference_energy_kwh is None:
        return None
    return reference_energy_kwh - proposed_energy_kwh


def calculate_annual_energy_cost(annual_energy_kwh: float | None, energy_price_per_kwh: float | None) -> float | None:
    if annual_energy_kwh is None or energy_price_per_kwh is None:
        return None
    return annual_energy_kwh * energy_price_per_kwh
