"""Enrichissement documentaire post-recommandation.

Execute UNIQUEMENT pour les configurations retenues dans le TOP final du moteur
de recommandation automatique (`app.services.recommendation_engine`) — jamais sur
l'ensemble des combinaisons Driver x Module x Lentille evaluees en amont.

Ce service ne modifie et ne peut jamais modifier : la compatibilite
(`is_compatible`), les regles bloquantes, le driver/module/lentille choisis ou
le score technique. Il ne fait que rechercher des passages documentaires
pertinents (via `HybridRetrievalService`) pour contextualiser la recommandation.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import Driver, LedModule, Lens, ProjectRequirement
from app.rag.embeddings import get_embedding_provider
from app.rag.search import HybridRetrievalService, SearchFilters, SearchResult, TextSearchService, VectorSearchService
from app.services.configuration_validation_service import ConfigurationEvaluation

_SUMMARY_MAX_LENGTH = 260


@dataclass
class EvidenceItem:
    category: str  # evidence_type (cf. RecommendationEvidence.evidence_type)
    document_id: int
    document_title: str
    section_title: str | None
    page_number: int | None
    relevance_score: float
    summary: str
    chunk_id: int


@dataclass
class EvidenceBundle:
    road_evidence: list[EvidenceItem] = field(default_factory=list)
    normative_evidence: list[EvidenceItem] = field(default_factory=list)
    photometric_evidence: list[EvidenceItem] = field(default_factory=list)
    product_evidence: list[EvidenceItem] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    confidence: str = "insufficient_evidence"  # high / medium / low / insufficient_evidence

    def all_items(self) -> list[EvidenceItem]:
        return self.road_evidence + self.normative_evidence + self.photometric_evidence + self.product_evidence


def _truncate(text: str, max_length: int = _SUMMARY_MAX_LENGTH) -> str:
    text = " ".join(text.split())
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."


class EvidenceEnrichmentService:
    """Construit un `EvidenceBundle` pour une configuration retenue dans le TOP final."""

    def __init__(self, retrieval_service: HybridRetrievalService, settings: Settings):
        self.retrieval_service = retrieval_service
        self.settings = settings

    def enrich(
        self,
        requirement: ProjectRequirement,
        driver: Driver | None,
        module: LedModule,
        lens: Lens | None,
        evaluation: ConfigurationEvaluation,
    ) -> EvidenceBundle:
        bundle = EvidenceBundle()
        if not self.settings.rag_enabled:
            bundle.missing_evidence.append("Recherche documentaire desactivee (RAG_ENABLED=false).")
            return bundle

        # --- ROAD / PHOTOMETRY QUERY --- construite a partir des donnees reellement fournies.
        road_terms = ["eclairage public routier", "classe d'eclairage", "performance photometrique"]
        if requirement.road_type:
            road_terms.append(requirement.road_type)
        if requirement.pole_height_m:
            road_terms.append(f"hauteur de mat {requirement.pole_height_m} m")
        if requirement.pole_spacing_m:
            road_terms.append(f"espacement candelabres {requirement.pole_spacing_m} m")
        road_terms.append(f"flux lumineux {module.luminous_flux_nominal_lm} lm")
        photometric_warnings = [
            w for w in evaluation.warnings if any(k in w.lower() for k in ("photom", "lentille", "distribution", "ies", "ldt"))
        ]
        road_terms.extend(photometric_warnings)
        bundle.road_evidence.extend(self._to_items(self._search(" ".join(road_terms)), "road_lighting"))

        photometry_query = "NM EN 13201 NM EN 13032 luminance eclairement uniformite eblouissement DIALux photometrie"
        bundle.photometric_evidence.extend(self._to_items(self._search(photometry_query), "photometric"))

        # --- MODULE QUERY ---
        module_query = "module LED performance securite IEC 62717 IEC 62031"
        bundle.product_evidence.extend(self._to_items(self._search(module_query), "module_standard"))

        # --- DRIVER QUERY --- adaptee au protocole reellement demande, jamais ajoutee par defaut.
        if driver is not None:
            driver_terms = ["driver LED securite appareillage IEC 61347-2-13"]
            wants_dali = requirement.protocol in ("DALI", "DALI-2") or driver.dali_2
            wants_d4i = requirement.protocol == "D4i" or driver.d4i
            if wants_dali:
                driver_terms.append("DALI DALI-2 commande numerique")
            if wants_d4i:
                driver_terms.append("D4i donnees intelligentes luminaire")
            bundle.product_evidence.extend(self._to_items(self._search(" ".join(driver_terms)), "driver_standard"))
        else:
            bundle.missing_evidence.append("Driver non selectionne : preuve documentaire driver non recherchee.")

        # --- LUMINAIRE QUERY ---
        luminaire_query = "luminaire eclairage public routier IEC NM 60598 protection IP IK"
        bundle.normative_evidence.extend(self._to_items(self._search(luminaire_query), "luminaire_standard"))

        # --- SMART LIGHTING --- seulement si le projet demande reellement un protocole de commande.
        if requirement.protocol in ("DALI", "DALI-2", "D4i"):
            smart_query = "DALI DALI-2 D4i IEC 62386 commande numerique telegestion smart lighting"
            bundle.normative_evidence.extend(self._to_items(self._search(smart_query), "smart_lighting"))

        # --- Validations documentaires restantes : jamais deduites comme satisfaites. ---
        if lens is None or not (lens.ies_file_available or lens.ldt_file_available):
            bundle.missing_evidence.append("Fichier photometrique IES/LDT de la lentille non verifie.")
        bundle.missing_evidence.append("Simulation DIALux non realisee pour cette configuration.")
        if driver is not None and driver.needs_manual_validation:
            bundle.missing_evidence.append("Preuve de conformite du driver a confirmer manuellement.")

        bundle.confidence = self._compute_confidence(bundle)
        return bundle

    def _search(self, query: str, **filter_kwargs) -> list[SearchResult]:
        filters = SearchFilters(**filter_kwargs) if filter_kwargs else None
        return self.retrieval_service.search(query, limit=self.settings.rag_top_k, filters=filters)

    @staticmethod
    def _to_items(results: list[SearchResult], category: str) -> list[EvidenceItem]:
        return [
            EvidenceItem(
                category=category,
                document_id=result.document_id,
                document_title=result.document_title,
                section_title=result.section_title,
                page_number=result.page_number,
                relevance_score=result.similarity_score,
                summary=_truncate(result.content),
                chunk_id=result.chunk_id,
            )
            for result in results
        ]

    @staticmethod
    def _compute_confidence(bundle: EvidenceBundle) -> str:
        if not bundle.all_items():
            return "insufficient_evidence"
        return compute_confidence(
            has_product=bool(bundle.product_evidence),
            has_photometric_or_road=bool(bundle.road_evidence or bundle.photometric_evidence),
            has_normative=bool(bundle.normative_evidence),
            missing_count=len(bundle.missing_evidence),
        )


def compute_confidence(
    has_product: bool, has_photometric_or_road: bool, has_normative: bool, missing_count: int
) -> str:
    """Politique de confiance documentaire (jamais utilisee pour modifier la compatibilite technique).

    HIGH : preuves couvrant produit + photometrie/route + cadre normatif, peu de manques.
    MEDIUM : plusieurs categories couvertes mais des validations manquent encore.
    LOW : preuves faibles ou indirectes (une seule categorie couverte).
    INSUFFICIENT_EVIDENCE : aucun passage pertinent retrouve (a appeler par le
    site appelant lorsque aucune preuve n'existe du tout).

    Fonction pure et partagee : utilisee a la fois au moment de l'enrichissement
    (`EvidenceEnrichmentService`) et a la lecture (recalcul depuis les lignes
    `RecommendationEvidence` persistees, cf. `app.api.routes.recommendations`).
    """
    coverage = sum([has_product, has_photometric_or_road, has_normative])
    if coverage >= 3 and missing_count <= 1:
        return "high"
    if coverage >= 2:
        return "medium"
    return "low"


def build_default_evidence_service(db: Session, settings: Settings) -> EvidenceEnrichmentService:
    """Assemble le pipeline de recherche par defaut (embedding -> hybrid) a partir des reglages."""
    embedding_provider = get_embedding_provider(settings)
    retrieval_service = HybridRetrievalService(
        vector_search=VectorSearchService(db, embedding_provider),
        text_search=TextSearchService(db),
        min_vector_score=settings.rag_min_score,
    )
    return EvidenceEnrichmentService(retrieval_service, settings)
