"""Efficacite lumineuse et pre-calcul photometrique estimatif (sections 3.E, 4, 5).

Les fonctions de cette section ne prouvent jamais une conformite EN/NM 13201 :
`estimated_average_illuminance_lux` et `uniformity_u0` sont des approximations
de pre-dimensionnement qui ne remplacent pas une simulation DIALux basee sur un
fichier IES/LDT (rappel porte par `CalculationValue.warning` cote service).
"""


def calculate_luminous_efficacy_lm_w(flux_lm: float | None, power_w: float | None) -> float | None:
    """efficacy = luminous_flux_lm / power_w. Ex: 15000 / 100 = 150 lm/W."""
    if flux_lm is None or power_w is None or power_w == 0:
        return None
    return flux_lm / power_w


def calculate_estimated_illuminance_lux(
    flux_lm: float | None,
    utilization_factor: float | None,
    maintenance_factor: float | None,
    area_m2: float | None,
) -> float | None:
    """E_moy ~= (flux x CU x MF) / area. Approximation de pre-dimensionnement uniquement."""
    if flux_lm is None or utilization_factor is None or maintenance_factor is None or area_m2 is None:
        return None
    if area_m2 == 0:
        return None
    return flux_lm * utilization_factor * maintenance_factor / area_m2


def calculate_uniformity_u0(e_min: float | None, e_avg: float | None) -> float | None:
    """U0 = E_min / E_avg. Ne calcule jamais E_min : n'active que si fourni (ex: import DIALux)."""
    if e_min is None or e_avg is None or e_avg == 0:
        return None
    return e_min / e_avg
