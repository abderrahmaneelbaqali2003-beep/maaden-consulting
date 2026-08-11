"""Tests de la base documentaire (V2 - RAG).

Les tests qui necessitent les tables `rag.*` / `consulting.recommendation_evidence`
sont ignores automatiquement (`pytest.skip`) tant que la migration
`a1c9e4d7f3b2` n'a pas ete appliquee. Aucune extension PostgreSQL native
n'est requise : les embeddings sont stockes en JSONB et la similarite
cosinus est calculee cote Python (cf. `app.rag.search`).
"""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.config import get_settings
from app.rag.chunking import SectionAwareChunkingStrategy
from app.rag.embeddings import MockEmbeddingProvider, get_embedding_provider
from app.rag.ingestion import DocumentIngestionService
from app.rag.parsing import ParsedPage, PdfDocumentParser
from app.rag.search import HybridRetrievalService, SearchFilters, TextSearchService, VectorSearchService
from app.services.evidence_enrichment_service import compute_confidence
from app.services.recommendation_engine import run_recommendation
from tests.factories import make_driver, make_lens, make_module, make_requirement

DOCUMENTS_DIR = Path(__file__).resolve().parents[1] / "data" / "documents"
settings = get_settings()


def _rag_schema_ready(db_session) -> bool:
    try:
        db_session.execute(text("SELECT 1 FROM rag.document_chunks LIMIT 1"))
        return True
    except ProgrammingError:
        db_session.rollback()
        return False


# --- Embeddings (aucune dependance externe) ---


def test_mock_embedding_provider_is_deterministic_and_has_configured_dimension():
    provider = MockEmbeddingProvider(dimension=32)
    v1 = provider.embed_query("eclairage public routier")
    v2 = provider.embed_query("eclairage public routier")
    v3 = provider.embed_query("driver LED")

    assert len(v1) == 32
    assert v1 == v2
    assert v1 != v3


def test_get_embedding_provider_defaults_to_mock():
    provider = get_embedding_provider(settings)
    assert isinstance(provider, MockEmbeddingProvider)
    assert provider.dimension == settings.embedding_dimension


# --- Chunking (respect des sections, chevauchement) ---


def test_section_aware_chunking_detects_headings_and_overlaps():
    text_page = (
        "1. Objectif et positionnement\n"
        + ("Une phrase de contexte reglementaire tres detaillee.\n" * 40)
        + "2. Cartographie des normes\n"
        + ("Une autre phrase decrivant une norme particuliere.\n" * 40)
    )
    pages = [ParsedPage(page_number=1, text=text_page)]

    chunks = SectionAwareChunkingStrategy(target_size=400, overlap=50).chunk(pages)

    assert len(chunks) >= 2
    section_titles = {c.section_title for c in chunks}
    assert "Objectif et positionnement" in section_titles
    assert "Cartographie des normes" in section_titles
    for chunk in chunks:
        assert chunk.page_number == 1
        assert chunk.content


def test_section_aware_chunking_does_not_fragment_tiny_paragraphs():
    text_page = "1. Introduction\nPhrase courte.\n2. Suite\nAutre phrase courte.\n3. Fin\nDerniere phrase."
    pages = [ParsedPage(page_number=1, text=text_page)]

    chunks = SectionAwareChunkingStrategy(target_size=800, overlap=100).chunk(pages)

    # Les 3 petites sections tiennent largement sous target_size : elles ne doivent
    # pas etre eclatees en 3 chunks separes.
    assert len(chunks) == 1


# --- Extraction PDF reelle (les 2 documents MAADEN, deja copies dans data/documents/) ---


@pytest.mark.parametrize(
    "file_name",
    ["Synthese_documentaire_NM13201_MAADEN.pdf", "Guide_Normes_Eclairage_Public_MAADEN_Consulting_2026.pdf"],
)
def test_pdf_parser_extracts_real_maaden_documents(file_name):
    file_path = DOCUMENTS_DIR / file_name
    if not file_path.exists():
        pytest.skip(f"{file_name} absent de {DOCUMENTS_DIR} (a copier avant indexation).")

    pages = PdfDocumentParser().parse(file_path)

    assert len(pages) > 0
    full_text = " ".join(p.text for p in pages)
    assert "13201" in full_text or "MAADEN" in full_text.upper()


# --- Confiance documentaire (fonction pure, jamais liee a la compatibilite technique) ---


@pytest.mark.parametrize(
    ("has_product", "has_photometric", "has_normative", "missing_count", "expected"),
    [
        (True, True, True, 0, "high"),
        (True, True, True, 3, "medium"),
        (True, True, False, 0, "medium"),
        (True, False, False, 0, "low"),
        (False, False, False, 0, "low"),
    ],
)
def test_compute_confidence_policy(has_product, has_photometric, has_normative, missing_count, expected):
    assert compute_confidence(has_product, has_photometric, has_normative, missing_count) == expected


# --- Ingestion + recherche hybride (necessite la migration a1c9e4d7f3b2) ---


def test_ingestion_and_hybrid_search_end_to_end(db_session):
    if not _rag_schema_ready(db_session):
        pytest.skip("Tables 'rag.*' absentes : lancer `alembic upgrade head` avant ce test d'integration.")

    file_path = DOCUMENTS_DIR / "Synthese_documentaire_NM13201_MAADEN.pdf"
    if not file_path.exists():
        pytest.skip(f"Document absent de {DOCUMENTS_DIR}.")

    embedding_provider = MockEmbeddingProvider(dimension=settings.embedding_dimension)
    service = DocumentIngestionService(db_session, settings, embedding_provider)

    result = service.ingest(
        file_path=file_path,
        title="Synthese documentaire NM 13 201",
        document_type="internal_summary",
        standard_family="road_lighting_13201",
        domain="eclairage_public",
    )
    # "already_indexed" si le document a deja ete indexe pour de vrai (ex: via
    # `python -m app.rag.index_default_documents`) avant l'execution des tests :
    # la ligne existe alors deja en base avec le meme hash de fichier.
    assert result.status in ("indexed", "already_indexed")
    assert result.chunks > 0

    # Reingestion du meme fichier : idempotent, ne duplique pas les chunks.
    result_again = service.ingest(
        file_path=file_path,
        title="Synthese documentaire NM 13 201",
        document_type="internal_summary",
        standard_family="road_lighting_13201",
        domain="eclairage_public",
    )
    assert result_again.status == "already_indexed"
    assert result_again.chunks == result.chunks

    retrieval = HybridRetrievalService(
        vector_search=VectorSearchService(db_session, embedding_provider),
        text_search=TextSearchService(db_session),
    )
    results = retrieval.search("classe d'eclairage NM 13201", limit=5)
    assert len(results) > 0

    filtered = retrieval.search(
        "classe d'eclairage", limit=5, filters=SearchFilters(standard_family="road_lighting_13201")
    )
    assert all(r.document_title == "Synthese documentaire NM 13 201" for r in filtered)


# --- Regression : la lecture V1 (dashboard, detail recommandation) ne doit jamais
# echouer, que la base documentaire soit vide/absente ou pleine. ---


def test_recommendation_read_endpoints_never_fail(client, db_session):
    module = make_module(
        db_session, luminous_flux_nominal_lm=6000, cct_nominal_k=4000, power_nominal_w=50, led_package="3535"
    )
    make_lens(db_session, compatible_led_package="3535", optical_cells_quantity=32)
    make_driver(db_session, output_power_max_w=150)
    req = make_requirement(db_session, persist=True, required_flux_lm=6000, required_cct_k=4000, max_power_w=60)

    run = run_recommendation(db_session, req)

    detail_response = client.get(f"/api/recommendations/{run.id}")
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["recommendations"]

    # Sans base documentaire (migration non appliquee) : `documentary_analysis` reste
    # None plutot que de faire echouer la lecture. Avec des documents reellement
    # indexes : structure valide, sans jamais influencer overall_score/is_compatible.
    analysis = body["recommendations"][0]["documentary_analysis"]
    if analysis is not None:
        assert analysis["confidence"] in ("high", "medium", "low", "insufficient_evidence")
        assert isinstance(analysis["evidence"], list)
        assert isinstance(analysis["missing_evidence"], list)
        assert analysis["evidence_count"] == len(analysis["evidence"])

    dashboard_response = client.get("/api/dashboard/summary")
    assert dashboard_response.status_code == 200

    history_response = client.get("/api/recommendations/history")
    assert history_response.status_code == 200

    dashboard_response = client.get("/api/dashboard/summary")
    assert dashboard_response.status_code == 200

    history_response = client.get("/api/recommendations/history")
    assert history_response.status_code == 200
