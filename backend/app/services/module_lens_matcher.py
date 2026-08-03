"""Evaluation deterministe de la compatibilite module <-> lentille (section 3 et 12.D).

Limitation connue (section 4) : la base de lentilles fournie ne contient aucun fichier
IES/LDT et de nombreuses dimensions sont absentes. Ce module ne bloque donc jamais une
configuration sur la seule absence de validation photometrique : il emet un avertissement
et laisse le statut global etre determine par le moteur de recommandation
(compatible_with_warning / manual_validation_required).
"""

from app.core.config import Settings
from app.database.models import LedModule, Lens, ProjectRequirement
from app.rules.results import CriterionResult, MatchEvaluation


def evaluate_lens_for_module(
    lens: Lens, module: LedModule, requirement: ProjectRequirement, settings: Settings
) -> MatchEvaluation:
    evaluation = MatchEvaluation(is_compatible=True)

    # --- Package LED declare compatible par le fabricant ---
    if lens.compatible_led_package:
        packages = [p.strip() for p in lens.compatible_led_package.split(",") if p.strip()]
        if module.led_package and module.led_package in packages:
            detail = f"Package '{module.led_package}' couvert par la lentille ({lens.compatible_led_package})."
            evaluation.validated_rules.append(
                f"Package LED du module ('{module.led_package}') couvert par la lentille."
            )
            evaluation.criteria.append(CriterionResult("package_led", "Compatibilite module-lentille", "valid", detail))
        elif module.led_package:
            evaluation.is_compatible = False
            message = (
                f"Package LED du module ('{module.led_package}') non couvert par la lentille "
                f"(packages compatibles : {lens.compatible_led_package})."
            )
            evaluation.blocking_reasons.append(message)
            evaluation.criteria.append(CriterionResult("package_led", "Compatibilite module-lentille", "blocking", message))
        else:
            message = "Package LED du module inconnu : compatibilite avec la lentille non verifiee."
            evaluation.warnings.append(message)
            evaluation.criteria.append(CriterionResult("package_led", "Compatibilite module-lentille", "not_verifiable", message))
    else:
        message = (
            "Compatibilite LED de la lentille non declaree par le fabricant dans la source : non verifiable "
            "(une lentille n'est jamais consideree compatible sur la seule base d'un package LED identique non confirme)."
        )
        evaluation.warnings.append(message)
        evaluation.criteria.append(CriterionResult("package_led", "Compatibilite module-lentille", "not_verifiable", message))

    # --- Nombre de cellules optiques vs nombre de LED du module (compatibilite mecanique) ---
    if lens.optical_cells_quantity is not None and module.led_quantity is not None:
        if lens.optical_cells_quantity == module.led_quantity:
            detail = f"{lens.optical_cells_quantity} cellules optiques = {module.led_quantity} LED du module."
            evaluation.validated_rules.append("Nombre de cellules optiques egal au nombre de LED du module.")
            evaluation.criteria.append(CriterionResult("mecanique", "Compatibilite mecanique", "valid", detail))
        else:
            evaluation.is_compatible = False
            message = (
                f"Nombre de cellules optiques de la lentille ({lens.optical_cells_quantity}) different du nombre "
                f"de LED du module ({module.led_quantity})."
            )
            evaluation.blocking_reasons.append(message)
            evaluation.criteria.append(CriterionResult("mecanique", "Compatibilite mecanique", "blocking", message))
    else:
        message = "Nombre de LED du module ou de cellules optiques de la lentille non renseigne : disposition non verifiee."
        evaluation.warnings.append(message)
        evaluation.criteria.append(CriterionResult("mecanique", "Compatibilite mecanique", "not_verifiable", message))

    # --- Fichier photometrique (IES/LDT) ---
    if not lens.ies_file_available and not lens.ldt_file_available:
        message = (
            "Aucun fichier IES/LDT disponible pour cette lentille : validation photometrique non effectuee, "
            "validation manuelle par un consultant requise avant chiffrage final."
        )
        evaluation.warnings.append(message)
        evaluation.criteria.append(CriterionResult("photometrie", "Photometrie (IES/LDT)", "warning", "Fichier IES/LDT absent : a valider manuellement."))
    else:
        evaluation.validated_rules.append("Fichier photometrique (IES/LDT) disponible pour cette lentille.")
        evaluation.criteria.append(CriterionResult("photometrie", "Photometrie (IES/LDT)", "valid", "Fichier IES/LDT disponible."))

    # --- Distribution adaptee au type de voie (avertissement uniquement, cf. section 4) ---
    if requirement.road_type and lens.iesna_distribution_type and lens.iesna_distribution_type != "unknown":
        message = (
            f"Distribution photometrique declaree : {lens.iesna_distribution_type}. Adequation avec le type de "
            f"voie '{requirement.road_type}' a confirmer manuellement (pas de simulation photometrique en V1)."
        )
        evaluation.warnings.append(message)
        evaluation.criteria.append(
            CriterionResult("distribution", "Distribution photometrique", "warning", f"Type {lens.iesna_distribution_type} declare, adequation a confirmer.")
        )
    else:
        evaluation.criteria.append(
            CriterionResult("distribution", "Distribution photometrique", "not_verifiable", "Type de voie ou distribution non renseigne(e).")
        )

    # --- Temperature ambiante ---
    if requirement.ambient_temperature_c is not None and lens.operating_temperature_max_c is not None:
        if lens.operating_temperature_max_c >= requirement.ambient_temperature_c:
            detail = f"{requirement.ambient_temperature_c} C dans la limite lentille ({lens.operating_temperature_max_c} C max)."
            evaluation.validated_rules.append("Temperature ambiante du projet compatible avec la lentille.")
            evaluation.criteria.append(CriterionResult("thermique_lentille", "Thermique (lentille)", "valid", detail))
        else:
            evaluation.is_compatible = False
            message = (
                f"Temperature ambiante du projet ({requirement.ambient_temperature_c} C) superieure a la limite "
                f"de la lentille ({lens.operating_temperature_max_c} C)."
            )
            evaluation.blocking_reasons.append(message)
            evaluation.criteria.append(CriterionResult("thermique_lentille", "Thermique (lentille)", "blocking", message))
    else:
        evaluation.criteria.append(
            CriterionResult(
                "thermique_lentille", "Thermique (lentille)", "not_verifiable", "Temperature ambiante ou limite lentille non renseignee."
            )
        )

    return evaluation
