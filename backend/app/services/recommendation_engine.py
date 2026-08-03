"""Orchestration du moteur de recommandation automatique (section 12, etapes B a G).

L'etape A (validation des entrees) est geree en amont par les schemas Pydantic
(app/schemas/recommendation.py) avant meme d'appeler ce module.

Toute la logique de compatibilite/scoring est deleguee a `ConfigurationValidationService`
(app/services/configuration_validation_service.py) — ce module se limite a l'orchestration :
selection des candidats (etape B), boucle de combinaison (etapes C/D), elimination (etape E)
et classement (etape G). Le meme service est reutilise par les modes manuel et semi-automatique
(`manual_configuration_service.py`, `hybrid_configuration_service.py`) : aucune regle n'est
dupliquee entre les trois modes.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.models import Driver, LedModule, Lens, ProjectRequirement, RecommendationResult, RecommendationRun
from app.services.candidate_selection import select_candidate_modules
from app.services.configuration_validation_service import ConfigurationEvaluation, ConfigurationValidationService

STATUS_MESSAGES = {
    "compatible": "{n} configuration(s) compatible(s) trouvee(s).",
    "compatible_with_warning": "{n} configuration(s) trouvee(s) avec avertissement(s) a verifier.",
    "manual_validation_required": (
        "{n} configuration(s) trouvee(s) necessitant une validation manuelle "
        "(ex: donnees photometriques ou lentille absentes)."
    ),
    "data_incomplete": "Des configurations existent mais les donnees disponibles sont insuffisantes pour les verifier completement.",
    "not_compatible": "Aucune configuration compatible trouvee avec les criteres actuels.",
    "impossible": "Aucune configuration possible avec les criteres actuels et les references disponibles dans la base.",
}


@dataclass
class RankedConfiguration:
    driver: Driver
    module: LedModule
    lens: Lens | None
    evaluation: ConfigurationEvaluation


def run_recommendation(
    db: Session, requirement: ProjectRequirement, settings: Settings | None = None
) -> RecommendationRun:
    settings = settings or get_settings()
    service = ConfigurationValidationService()

    candidate_modules = select_candidate_modules(db, requirement, settings)
    all_drivers = db.query(Driver).filter(Driver.is_active.is_(True)).all()
    all_lenses = db.query(Lens).filter(Lens.is_active.is_(True)).all()

    drivers_rejected = 0
    modules_rejected = 0
    lenses_rejected = 0
    ranked: list[RankedConfiguration] = []

    if not candidate_modules:
        modules_rejected = db.query(LedModule).filter(LedModule.is_active.is_(True)).count()

    for module in candidate_modules:
        # Pre-filtre des lentilles compatibles avec ce module (independant du driver) :
        # evalue via le service commun avec driver=None pour n'obtenir que le verdict lentille<->module.
        lens_matches: list[Lens] = []
        for lens in all_lenses:
            lens_only = service.evaluate(None, module, lens, requirement, settings, skip_explanation=True)
            if lens_only.is_compatible:
                lens_matches.append(lens)
            else:
                lenses_rejected += 1

        any_driver_compatible = False
        for driver in all_drivers:
            driver_only = service.evaluate(driver, module, None, requirement, settings, skip_explanation=True)
            if not driver_only.is_compatible:
                drivers_rejected += 1
                continue
            any_driver_compatible = True

            if lens_matches:
                for lens in lens_matches:
                    evaluation = service.evaluate(driver, module, lens, requirement, settings, skip_explanation=True)
                    ranked.append(RankedConfiguration(driver, module, lens, evaluation))
            else:
                evaluation = service.evaluate(driver, module, None, requirement, settings, skip_explanation=True)
                ranked.append(RankedConfiguration(driver, module, None, evaluation))

        if not any_driver_compatible:
            modules_rejected += 1

    # Seules les combinaisons sans regle bloquante sont classees (etape E - elimination).
    ranked = [r for r in ranked if r.evaluation.is_compatible]
    ranked.sort(key=lambda r: r.evaluation.scores.overall, reverse=True)
    top = ranked[: settings.max_results]

    status = top[0].evaluation.status if top else "impossible"
    blocking_reasons, suggestions = _build_impossible_reasons(status, candidate_modules)

    run = RecommendationRun(
        request_id=uuid.uuid4(),
        requirement_id=requirement.id,
        status=status,
        message=STATUS_MESSAGES[status].format(n=len(top)),
        drivers_rejected=drivers_rejected,
        modules_rejected=modules_rejected,
        lenses_rejected=lenses_rejected,
        blocking_reasons=blocking_reasons,
        suggestions=suggestions,
    )
    db.add(run)
    db.flush()

    for rank_number, item in enumerate(top, start=1):
        # Reevaluation finale (avec explication) uniquement pour les configurations retenues.
        final = service.evaluate(item.driver, item.module, item.lens, requirement, settings, rank=rank_number)
        db.add(
            RecommendationResult(
                run_id=run.id,
                rank=rank_number,
                driver_id=item.driver.id,
                module_id=item.module.id,
                lens_id=item.lens.id if item.lens else None,
                overall_score=final.scores.overall,
                score_electrical=final.scores.electrical,
                score_photometric=final.scores.photometric,
                score_mechanical=final.scores.mechanical,
                score_thermal=final.scores.thermal,
                score_data_quality=final.scores.data_quality,
                validated_rules=final.validated_rules,
                warnings=final.warnings,
                blocking_reasons=final.blocking_reasons,
                explanation=final.explanation,
                validation_status="pending",
            )
        )

    db.commit()
    db.refresh(run)
    return run


def _build_impossible_reasons(status: str, candidate_modules: list[LedModule]) -> tuple[list[str], list[str]]:
    if status != "impossible":
        return [], []
    if not candidate_modules:
        return (
            [
                "Aucun module de la base ne satisfait simultanement le flux demande (avec tolerance), "
                "la puissance maximale et la CCT demandee."
            ],
            [
                "Augmenter la puissance maximale autorisee ou elargir la CCT demandee.",
                "Ajouter de nouvelles references de modules dans la base.",
            ],
        )
    return (
        [
            "Aucun driver de la base ne couvre simultanement la tension, le courant et la puissance requis "
            "par les modules compatibles trouves."
        ],
        [
            "Modifier la tension ou le courant nominal demandes.",
            "Ajouter de nouvelles references de drivers dans la base.",
        ],
    )
