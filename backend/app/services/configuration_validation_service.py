"""Service commun de validation d'une configuration (driver + module + lentille).

Point d'entree UNIQUE pour toute evaluation de compatibilite driver/module/lentille.
Reutilise par :
 - `recommendation_engine.py` (mode automatique : boucle sur de nombreuses combinaisons)
 - `manual_configuration_service.py` (mode manuel : une combinaison choisie par le consultant)
 - `hybrid_configuration_service.py` (mode semi-automatique : composants imposes + recherche du reste)

Aucune regle de compatibilite electrique/mecanique n'est reimplementee ici : ce service
orchestre les matchers deterministes existants (`driver_module_matcher`, `module_lens_matcher`)
et le moteur de scoring, puis determine un statut et une matrice de criteres uniques par
configuration evaluee. Modifier une regle de compatibilite se fait donc a un seul endroit
(les matchers), jamais dans ce service ni dans ses appelants.
"""

from dataclasses import dataclass, field

from app.core.config import Settings, get_settings
from app.database.models import Driver, LedModule, Lens, ProjectRequirement
from app.rules.results import CriterionResult
from app.services.driver_module_matcher import evaluate_driver_for_module
from app.services.explanation_engine import ExplanationProvider, TemplateExplanationProvider
from app.services.module_lens_matcher import evaluate_lens_for_module
from app.services.scoring_engine import ScoreBreakdown, compute_scores


@dataclass
class ConfigurationEvaluation:
    status: str  # compatible / compatible_with_warning / data_incomplete / manual_validation_required / not_compatible
    is_compatible: bool  # False si au moins une regle bloquante est violee
    needs_manual_validation: bool
    scores: ScoreBreakdown
    validated_rules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    criteria: list[CriterionResult] = field(default_factory=list)
    explanation: str = ""


class ConfigurationValidationService:
    """Evalue une combinaison (driver, module, lentille) par rapport a un besoin projet."""

    def __init__(self, explanation_provider: ExplanationProvider | None = None):
        self._explanation_provider = explanation_provider or TemplateExplanationProvider()

    def evaluate(
        self,
        driver: Driver | None,
        module: LedModule,
        lens: Lens | None,
        requirement: ProjectRequirement,
        settings: Settings | None = None,
        rank: int = 1,
        skip_explanation: bool = False,
    ) -> ConfigurationEvaluation:
        settings = settings or get_settings()

        validated_rules: list[str] = []
        warnings: list[str] = []
        blocking_reasons: list[str] = []
        criteria: list[CriterionResult] = []

        if driver is not None:
            driver_eval = evaluate_driver_for_module(driver, module, requirement, settings)
            validated_rules += driver_eval.validated_rules
            warnings += driver_eval.warnings
            blocking_reasons += driver_eval.blocking_reasons
            criteria += driver_eval.criteria
        else:
            driver_eval = None
            criteria.append(CriterionResult("driver", "Driver", "not_verifiable", "Aucun driver selectionne."))

        if lens is not None:
            lens_eval = evaluate_lens_for_module(lens, module, requirement, settings)
            validated_rules += lens_eval.validated_rules
            warnings += lens_eval.warnings
            blocking_reasons += lens_eval.blocking_reasons
            criteria += lens_eval.criteria
        else:
            lens_eval = None
            criteria.append(CriterionResult("lentille", "Lentille", "not_verifiable", "Aucune lentille selectionnee."))

        is_compatible = not blocking_reasons

        needs_manual_validation = (
            driver is None
            or lens is None
            or (driver is not None and driver.needs_manual_validation)
            or module.needs_manual_validation
            or (lens is not None and lens.needs_manual_validation)
            or (lens is not None and not (lens.ies_file_available or lens.ldt_file_available))
        )

        mechanical_warnings_count = len(lens_eval.warnings) if lens_eval else 0
        scores = compute_scores(driver, module, lens, requirement, settings, mechanical_warnings_count)

        status = self._determine_status(is_compatible, validated_rules, needs_manual_validation, warnings)

        explanation = ""
        if not skip_explanation:
            explanation = self._explanation_provider.explain(rank, driver, module, lens, scores, warnings)

        return ConfigurationEvaluation(
            status=status,
            is_compatible=is_compatible,
            needs_manual_validation=needs_manual_validation,
            scores=scores,
            validated_rules=validated_rules,
            warnings=warnings,
            blocking_reasons=blocking_reasons,
            criteria=criteria,
            explanation=explanation,
        )

    @staticmethod
    def _determine_status(
        is_compatible: bool, validated_rules: list[str], needs_manual_validation: bool, warnings: list[str]
    ) -> str:
        if not is_compatible:
            return "not_compatible"
        if not validated_rules:
            return "data_incomplete"
        if needs_manual_validation:
            return "manual_validation_required"
        if warnings:
            return "compatible_with_warning"
        return "compatible"
