"""Grandeurs electriques (section 3.A-D).

Fonctions pures, deterministes, sans arrondi (l'arrondi n'est applique qu'a
l'affichage, dans `service.py`). Retournent `None` quand une entree
necessaire est absente ou que le calcul n'a pas de sens (ex: puissance
nulle au denominateur) : c'est a l'appelant de traduire `None` en
`status="not_calculable"` + message explicite, jamais en 0.
"""


def calculate_module_power_w(voltage_v: float | None, current_ma: float | None) -> float | None:
    """P = V x I(mA) / 1000. Ex: 48 V x 700 mA = 33.6 W."""
    if voltage_v is None or current_ma is None:
        return None
    return voltage_v * current_ma / 1000


def calculate_power_consistency_diff_percent(calculated_w: float | None, nominal_w: float | None) -> float | None:
    """Ecart entre la puissance calculee (V x I) et la puissance nominale fabricant.

    Ne remplace jamais la valeur fabricant : sert uniquement a signaler un
    ecart important (avertissement genere par l'appelant).
    """
    if calculated_w is None or nominal_w is None or nominal_w == 0:
        return None
    return (calculated_w - nominal_w) / nominal_w * 100


def calculate_driver_required_power_w(module_power_w: float | None, safety_factor: float | None) -> float | None:
    """P_driver_required = P_module x safety_factor (parametre de securite existant, reutilise)."""
    if module_power_w is None or safety_factor is None:
        return None
    return module_power_w * safety_factor


def calculate_driver_loading_percent(module_power_w: float | None, driver_power_max_w: float | None) -> float | None:
    """driver_loading_percent = P_module / P_driver_max x 100."""
    if module_power_w is None or driver_power_max_w is None or driver_power_max_w == 0:
        return None
    return module_power_w / driver_power_max_w * 100


def calculate_power_margin_percent(driver_power_max_w: float | None, module_power_w: float | None) -> float | None:
    """power_margin_percent = (P_driver_max / P_module - 1) x 100.

    Formule unique, reutilisee par `app.services.driver_module_matcher`
    (evaluation de compatibilite) et par `CalculationService` (affichage) :
    jamais deux implementations divergentes de la meme grandeur.
    """
    if driver_power_max_w is None or module_power_w is None or module_power_w == 0:
        return None
    return (driver_power_max_w / module_power_w - 1) * 100
