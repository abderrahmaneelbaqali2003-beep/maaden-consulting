"""Service de selection manuelle assistee (mode 'manual').

L'utilisateur choisit lui-meme le module, le driver et la lentille. Ce service ne fait
QUE reutiliser `ConfigurationValidationService` pour evaluer le choix et proposer des
alternatives — aucune regle de compatibilite n'est reimplementee ici.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.models import Driver, LedModule, Lens, ProjectRequirement
from app.services.configuration_validation_service import ConfigurationEvaluation, ConfigurationValidationService


@dataclass
class AlternativeConfiguration:
    driver: Driver | None
    module: LedModule
    lens: Lens | None
    evaluation: ConfigurationEvaluation


class ManualConfigurationService:
    def __init__(self, validation_service: ConfigurationValidationService | None = None):
        self._service = validation_service or ConfigurationValidationService()

    def validate(
        self,
        driver: Driver | None,
        module: LedModule,
        lens: Lens | None,
        requirement: ProjectRequirement,
        settings: Settings | None = None,
    ) -> ConfigurationEvaluation:
        settings = settings or get_settings()
        return self._service.evaluate(driver, module, lens, requirement, settings, rank=1)

    def find_alternatives(
        self,
        db: Session,
        module: LedModule,
        requirement: ProjectRequirement,
        settings: Settings | None = None,
        exclude_driver_id: int | None = None,
        exclude_lens_id: int | None = None,
        limit: int = 3,
    ) -> list[AlternativeConfiguration]:
        """Cherche jusqu'a `limit` combinaisons compatibles alternatives pour le MEME module,
        en excluant la combinaison actuellement selectionnee, classees par score decroissant."""
        settings = settings or get_settings()

        all_drivers = db.query(Driver).filter(Driver.is_active.is_(True)).all()
        all_lenses = db.query(Lens).filter(Lens.is_active.is_(True)).all()

        lens_matches = [
            lens
            for lens in all_lenses
            if self._service.evaluate(None, module, lens, requirement, settings, skip_explanation=True).is_compatible
        ]

        alternatives: list[AlternativeConfiguration] = []
        for driver in all_drivers:
            driver_eval = self._service.evaluate(driver, module, None, requirement, settings, skip_explanation=True)
            if not driver_eval.is_compatible:
                continue
            lens_options = lens_matches or [None]
            for lens in lens_options:
                if driver.id == exclude_driver_id and (lens is None) == (exclude_lens_id is None) and (
                    lens is None or lens.id == exclude_lens_id
                ):
                    continue
                evaluation = self._service.evaluate(driver, module, lens, requirement, settings, skip_explanation=True)
                if evaluation.is_compatible:
                    alternatives.append(AlternativeConfiguration(driver, module, lens, evaluation))

        alternatives.sort(key=lambda a: a.evaluation.scores.overall, reverse=True)
        return alternatives[:limit]
