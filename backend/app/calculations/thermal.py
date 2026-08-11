"""Marge thermique (section 3.H).

Ne cree pas de contradiction avec les regles bloquantes deja evaluees par
`app.services.driver_module_matcher` / `module_lens_matcher` (qui decident de
la compatibilite) : ce module se contente d'exposer la marge en degres, a
titre informatif.
"""


def calculate_thermal_margin_c(
    component_max_temperature_c: float | None, project_ambient_temperature_c: float | None
) -> float | None:
    """marge = temperature_max_composant - temperature_ambiante_projet. Ex: 60 - 45 = 15 C."""
    if component_max_temperature_c is None or project_ambient_temperature_c is None:
        return None
    return component_max_temperature_c - project_ambient_temperature_c
