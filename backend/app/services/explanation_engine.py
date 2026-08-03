"""Generation d'explications (section 16).

`ExplanationProvider` est une interface abstraite : la V1 utilise uniquement
`TemplateExplanationProvider` (aucun LLM). Une future `LLMExplanationProvider` pourra
etre branchee sans modifier le moteur de compatibilite, qui reste 100% deterministe.
"""

from abc import ABC, abstractmethod

from app.database.models import Driver, LedModule, Lens
from app.services.scoring_engine import ScoreBreakdown


class ExplanationProvider(ABC):
    @abstractmethod
    def explain(
        self,
        rank: int,
        driver: Driver | None,
        module: LedModule,
        lens: Lens | None,
        scores: ScoreBreakdown,
        warnings: list[str],
    ) -> str: ...


class TemplateExplanationProvider(ExplanationProvider):
    def explain(
        self,
        rank: int,
        driver: Driver | None,
        module: LedModule,
        lens: Lens | None,
        scores: ScoreBreakdown,
        warnings: list[str],
    ) -> str:
        parts = [f"Configuration classee n°{rank} avec un score global de {scores.overall}/100."]

        if driver is not None:
            parts.append(
                f"Le driver {driver.manufacturer.name} {driver.reference} couvre la tension nominale du module "
                f"({driver.output_voltage_min_v}-{driver.output_voltage_max_v} V) et sa plage de courant "
                f"({driver.output_current_min_ma}-{driver.output_current_max_ma} mA), avec une puissance maximale "
                f"de {driver.output_power_max_w} W pour un module consommant {module.power_nominal_w or '?'} W."
            )
        else:
            parts.append("Aucun driver selectionne pour cette configuration.")

        parts.append(
            f"Le module {module.manufacturer.name} {module.reference} delivre {module.luminous_flux_nominal_lm} lm "
            f"a {module.cct_nominal_k} K, avec un score electrique de {scores.electrical}/35 et un score "
            f"flux/CCT de {scores.photometric}/25."
        )

        if lens is not None:
            parts.append(
                f"La lentille {lens.manufacturer.name} {lens.reference} obtient un score mecanique/optique de "
                f"{scores.mechanical}/20."
            )
        else:
            parts.append("Aucune lentille compatible n'a pu etre associee a cette configuration.")

        parts.append(f"Score thermique : {scores.thermal}/10. Score de qualite des donnees : {scores.data_quality}/10.")

        if warnings:
            parts.append("Points a verifier avant validation finale : " + " ".join(warnings))

        return " ".join(parts)
