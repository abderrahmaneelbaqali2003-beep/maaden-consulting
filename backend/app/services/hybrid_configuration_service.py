"""Service de selection semi-automatique (mode 'hybrid').

L'utilisateur impose 1 ou 2 composants (driver, module et/ou lentille) ; le service
recherche le(s) composant(s) restant(s) parmi les references compatibles. Comme pour
le mode manuel, toute la logique de compatibilite est deleguee a
`ConfigurationValidationService` — ce module se limite a construire les listes de
candidats (les composants imposes deviennent des contraintes obligatoires : ils ne
sont jamais ecartes, meme si le resultat final est incompatible, afin que l'utilisateur
comprenne pourquoi).
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.models import Driver, LedModule, Lens, ProjectRequirement
from app.services.candidate_selection import select_candidate_modules
from app.services.configuration_validation_service import ConfigurationEvaluation, ConfigurationValidationService


class MissingRequirementFieldsError(ValueError):
    """Leve quand le module n'est pas impose et que les criteres necessaires a sa
    recherche (flux, CCT) sont absents des besoins projet."""


@dataclass
class HybridCandidate:
    driver: Driver | None
    module: LedModule
    lens: Lens | None
    evaluation: ConfigurationEvaluation


@dataclass
class HybridResult:
    best: HybridCandidate | None
    alternatives: list[HybridCandidate]


class HybridConfigurationService:
    def __init__(self, validation_service: ConfigurationValidationService | None = None):
        self._service = validation_service or ConfigurationValidationService()

    def recommend_missing(
        self,
        db: Session,
        requirement: ProjectRequirement,
        settings: Settings | None,
        fixed_driver: Driver | None,
        fixed_module: LedModule | None,
        fixed_lens: Lens | None,
    ) -> HybridResult:
        settings = settings or get_settings()

        if fixed_module is not None:
            modules_pool = [fixed_module]
        else:
            if requirement.required_flux_lm is None or requirement.required_cct_k is None:
                raise MissingRequirementFieldsError(
                    "Le flux lumineux demande et la CCT sont necessaires pour rechercher un module "
                    "lorsque celui-ci n'est pas impose."
                )
            modules_pool = select_candidate_modules(db, requirement, settings)
            if not modules_pool:
                return HybridResult(best=None, alternatives=[])

        drivers_pool = (
            [fixed_driver] if fixed_driver is not None else db.query(Driver).filter(Driver.is_active.is_(True)).all()
        )
        all_lenses = db.query(Lens).filter(Lens.is_active.is_(True)).all()

        results: list[HybridCandidate] = []
        for module in modules_pool:
            if fixed_lens is not None:
                lens_options = [fixed_lens]
            else:
                matches = [
                    lens
                    for lens in all_lenses
                    if self._service.evaluate(None, module, lens, requirement, settings, skip_explanation=True).is_compatible
                ]
                lens_options = matches if matches else [None]

            for driver in drivers_pool:
                for lens in lens_options:
                    evaluation = self._service.evaluate(driver, module, lens, requirement, settings, skip_explanation=True)
                    results.append(HybridCandidate(driver, module, lens, evaluation))

        if not results:
            return HybridResult(best=None, alternatives=[])

        # Priorite aux configurations sans regle bloquante ; a defaut, on remonte quand meme
        # la moins mauvaise pour expliquer pourquoi le(s) composant(s) impose(s) posent probleme.
        compatible = [r for r in results if r.evaluation.is_compatible]
        pool = compatible if compatible else results
        pool.sort(key=lambda r: r.evaluation.scores.overall, reverse=True)

        best = pool[0]
        final_evaluation = self._service.evaluate(best.driver, best.module, best.lens, requirement, settings, rank=1)
        best = HybridCandidate(best.driver, best.module, best.lens, final_evaluation)

        alternatives = [r for r in pool[1:6] if r.evaluation.is_compatible]

        return HybridResult(best=best, alternatives=alternatives)
