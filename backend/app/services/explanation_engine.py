"""Generation d'explications (section 16).

`ExplanationProvider` est une interface abstraite : la V1 utilise uniquement
`TemplateExplanationProvider` (aucun LLM). Une future `LLMExplanationProvider` pourra
etre branchee sans modifier le moteur de compatibilite, qui reste 100% deterministe.

V2 (RAG) : `explain()` accepte un `evidence` optionnel (`EvidenceBundle`, voir
`app.services.evidence_enrichment_service`) pour enrichir le texte d'un rappel du
cadre normatif associe et des validations documentaires restantes. Les appels
existants (sans `evidence`) restent inchanges — argument optionnel par defaut `None`.

Formulations volontairement prudentes : un passage documentaire retrouve ne
prouve jamais a lui seul la conformite reglementaire ("norme associee",
"reference documentaire pertinente", "a verifier"), jamais "conforme IEC X".
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.database.models import Driver, LedModule, Lens
from app.services.scoring_engine import ScoreBreakdown

if TYPE_CHECKING:
    from app.services.evidence_enrichment_service import EvidenceBundle


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
        evidence: "EvidenceBundle | None" = None,
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
        evidence: "EvidenceBundle | None" = None,
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

        if evidence is not None:
            parts.append(self._evidence_paragraph(evidence))

        return " ".join(p for p in parts if p)

    @staticmethod
    def _evidence_paragraph(evidence: "EvidenceBundle") -> str:
        items = evidence.all_items()
        if not items:
            return (
                "Aucune reference documentaire pertinente n'a ete retrouvee dans la base normative pour cette "
                "configuration (confiance documentaire : preuve insuffisante)."
            )

        seen_documents = []
        for item in items:
            label = f"{item.document_title}" + (f" ({item.section_title})" if item.section_title else "")
            if label not in seen_documents:
                seen_documents.append(label)

        segments = [
            "Cadre normatif associe (reference documentaire pertinente, a verifier avec la source officielle) : "
            + "; ".join(seen_documents[:5])
            + "."
        ]
        if evidence.missing_evidence:
            segments.append("Validations documentaires manquantes : " + "; ".join(evidence.missing_evidence) + ".")
        segments.append(f"Confiance documentaire : {evidence.confidence}.")
        return " ".join(segments)
