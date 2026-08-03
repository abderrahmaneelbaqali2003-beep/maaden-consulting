"""Evaluation deterministe de la compatibilite driver <-> module (section 3 et 12.C).

Chaque verification qui ne peut pas etre effectuee par manque de donnee genere un
avertissement (jamais une invention de valeur) et n'empeche pas la suite du calcul,
sauf les regles explicitement bloquantes dont les donnees sont presentes.
"""

from app.core.config import Settings
from app.database.models import Driver, LedModule, ProjectRequirement
from app.rules.protocol_matching import resolve_protocol_column
from app.rules.results import CriterionResult, MatchEvaluation


def evaluate_driver_for_module(
    driver: Driver, module: LedModule, requirement: ProjectRequirement, settings: Settings
) -> MatchEvaluation:
    evaluation = MatchEvaluation(is_compatible=True)

    # --- Tension : output_voltage_min_v <= module.input_voltage_nominal_v <= output_voltage_max_v ---
    if module.input_voltage_nominal_v is not None:
        if driver.output_voltage_min_v <= module.input_voltage_nominal_v <= driver.output_voltage_max_v:
            detail = (
                f"{module.input_voltage_nominal_v} V dans la plage "
                f"{driver.output_voltage_min_v}-{driver.output_voltage_max_v} V."
            )
            evaluation.validated_rules.append(f"Tension module ({module.input_voltage_nominal_v} V) dans la plage de sortie du driver ({driver.output_voltage_min_v}-{driver.output_voltage_max_v} V).")
            evaluation.criteria.append(CriterionResult("tension", "Tension", "valid", detail))
        else:
            evaluation.is_compatible = False
            message = (
                f"Tension module ({module.input_voltage_nominal_v} V) hors plage du driver "
                f"({driver.output_voltage_min_v}-{driver.output_voltage_max_v} V)."
            )
            evaluation.blocking_reasons.append(message)
            evaluation.criteria.append(CriterionResult("tension", "Tension", "blocking", message))
    else:
        message = "Tension nominale du module inconnue : compatibilite electrique de tension non verifiee."
        evaluation.warnings.append(message)
        evaluation.criteria.append(CriterionResult("tension", "Tension", "not_verifiable", message))

    # --- Courant : plage driver, tolerance si driver a courant fixe ---
    if (
        module.current_nominal_ma is not None
        and driver.output_current_min_ma is not None
        and driver.output_current_max_ma is not None
    ):
        is_fixed_current = driver.output_current_min_ma == driver.output_current_max_ma
        tolerance = settings.current_fixed_tolerance_ma if is_fixed_current else 0.0
        low, high = driver.output_current_min_ma - tolerance, driver.output_current_max_ma + tolerance
        if low <= module.current_nominal_ma <= high:
            detail = f"{module.current_nominal_ma} mA accepte (plage driver {driver.output_current_min_ma}-{driver.output_current_max_ma} mA)."
            evaluation.validated_rules.append(
                f"Courant module ({module.current_nominal_ma} mA) dans la plage du driver "
                f"({driver.output_current_min_ma}-{driver.output_current_max_ma} mA)."
            )
            evaluation.criteria.append(CriterionResult("courant", "Courant", "valid", detail))
        else:
            evaluation.is_compatible = False
            message = (
                f"Courant module ({module.current_nominal_ma} mA) hors plage du driver "
                f"({driver.output_current_min_ma}-{driver.output_current_max_ma} mA)."
            )
            evaluation.blocking_reasons.append(message)
            evaluation.criteria.append(CriterionResult("courant", "Courant", "blocking", message))
    else:
        message = "Courant nominal du module ou plage de courant du driver inconnu(e) : compatibilite de courant non verifiee."
        evaluation.warnings.append(message)
        evaluation.criteria.append(CriterionResult("courant", "Courant", "not_verifiable", message))

    # --- Marge de puissance (safety_factor configurable) ---
    if module.power_nominal_w is not None:
        required_power = module.power_nominal_w * settings.safety_factor
        if driver.output_power_max_w >= required_power:
            margin_percent = (driver.output_power_max_w / module.power_nominal_w - 1) * 100
            status = "valid" if margin_percent >= (settings.safety_factor - 1) * 100 + 5 else "warning"
            detail = f"Marge de {margin_percent:.0f}% (minimum requis : {(settings.safety_factor - 1) * 100:.0f}%)."
            evaluation.validated_rules.append(
                f"Marge de puissance de {margin_percent:.0f}% (minimum requis : "
                f"{(settings.safety_factor - 1) * 100:.0f}%)."
            )
            if status == "warning":
                evaluation.warnings.append(f"Marge de puissance faible : {detail}")
            evaluation.criteria.append(CriterionResult("puissance", "Puissance", status, detail))
        else:
            evaluation.is_compatible = False
            message = (
                f"Puissance max. du driver ({driver.output_power_max_w} W) insuffisante pour le module "
                f"({module.power_nominal_w} W) avec la marge de securite configuree ({settings.safety_factor})."
            )
            evaluation.blocking_reasons.append(message)
            evaluation.criteria.append(CriterionResult("puissance", "Puissance", "blocking", message))
    else:
        message = "Puissance nominale du module inconnue : marge de securite non verifiee."
        evaluation.warnings.append(message)
        evaluation.criteria.append(CriterionResult("puissance", "Puissance", "not_verifiable", message))

    # --- Protocole demande ---
    if requirement.protocol:
        column = resolve_protocol_column(requirement.protocol)
        if column is None:
            message = f"Protocole demande '{requirement.protocol}' non reconnu par le moteur : non verifie."
            evaluation.warnings.append(message)
            evaluation.criteria.append(CriterionResult("protocole", "Protocole", "not_verifiable", message))
        elif getattr(driver, column, False):
            detail = f"{requirement.protocol} supporte par le driver."
            evaluation.validated_rules.append(f"Protocole '{requirement.protocol}' supporte par le driver.")
            evaluation.criteria.append(CriterionResult("protocole", "Protocole", "valid", detail))
        else:
            evaluation.is_compatible = False
            message = f"Le driver ne supporte pas le protocole demande '{requirement.protocol}'."
            evaluation.blocking_reasons.append(message)
            evaluation.criteria.append(CriterionResult("protocole", "Protocole", "blocking", message))
    else:
        evaluation.criteria.append(
            CriterionResult("protocole", "Protocole", "not_verifiable", "Aucun protocole demande : non verifie.")
        )

    # --- Temperature ambiante ---
    if requirement.ambient_temperature_c is not None:
        if driver.ambient_temperature_max_c is not None:
            if driver.ambient_temperature_max_c >= requirement.ambient_temperature_c:
                detail = (
                    f"{requirement.ambient_temperature_c} C dans la limite driver "
                    f"({driver.ambient_temperature_max_c} C max)."
                )
                evaluation.validated_rules.append("Temperature ambiante du projet dans la plage du driver.")
                evaluation.criteria.append(CriterionResult("thermique_driver", "Thermique (driver)", "valid", detail))
            else:
                evaluation.is_compatible = False
                message = (
                    f"Temperature ambiante du projet ({requirement.ambient_temperature_c} C) superieure a la "
                    f"limite du driver ({driver.ambient_temperature_max_c} C)."
                )
                evaluation.blocking_reasons.append(message)
                evaluation.criteria.append(CriterionResult("thermique_driver", "Thermique (driver)", "blocking", message))
        else:
            message = "Temperature ambiante maximale du driver inconnue : compatibilite thermique non verifiee."
            evaluation.warnings.append(message)
            evaluation.criteria.append(CriterionResult("thermique_driver", "Thermique (driver)", "not_verifiable", message))
    else:
        evaluation.criteria.append(
            CriterionResult(
                "thermique_driver", "Thermique (driver)", "not_verifiable", "Temperature ambiante non fournie."
            )
        )

    return evaluation
