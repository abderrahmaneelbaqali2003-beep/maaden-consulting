from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.database.models import RagDocument
from app.rag.embeddings import get_embedding_provider
from app.rag.index_default_documents import DEFAULT_DOCUMENTS, DOCUMENTS_DIR
from app.rag.ingestion import DocumentIngestionService
from app.rag.search import HybridRetrievalService, SearchFilters, TextSearchService, VectorSearchService
from app.schemas.rag import (
    RagDocumentOut,
    RagReindexDocumentOut,
    RagReindexResponse,
    RagSearchRequest,
    RagSearchResponse,
    RagSearchResultOut,
)

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/documents", response_model=list[RagDocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(RagDocument).order_by(RagDocument.id).all()


@router.post("/search", response_model=RagSearchResponse)
def search_documents(payload: RagSearchRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    embedding_provider = get_embedding_provider(settings)
    retrieval_service = HybridRetrievalService(
        vector_search=VectorSearchService(db, embedding_provider),
        text_search=TextSearchService(db),
        min_vector_score=settings.rag_min_score,
    )
    filters = SearchFilters(
        document_type=payload.document_type,
        standard_family=payload.standard_family,
        domain=payload.domain,
        authority_level=payload.authority_level,
    )
    results = retrieval_service.search(payload.query, limit=payload.limit, filters=filters)
    return RagSearchResponse(
        results=[
            RagSearchResultOut(
                document_title=r.document_title,
                section_title=r.section_title,
                page_number=r.page_number,
                content=r.content,
                similarity_score=r.similarity_score,
            )
            for r in results
        ]
    )


@router.post("/reindex", response_model=RagReindexResponse)
def reindex_documents(db: Session = Depends(get_db)):
    """Reindexe les 2 documents par defaut. N'expose aucun chemin filesystem interne."""
    settings = get_settings()
    embedding_provider = get_embedding_provider(settings)
    service = DocumentIngestionService(db, settings, embedding_provider)

    summaries = []
    for config in DEFAULT_DOCUMENTS:
        file_path = DOCUMENTS_DIR / config["file_name"]
        if not file_path.exists():
            summaries.append(
                RagReindexDocumentOut(title=config["title"], status="missing", pages=0, chunks=0)
            )
            continue
        result = service.ingest(
            file_path=file_path,
            title=config["title"],
            document_type=config["document_type"],
            standard_family=config["standard_family"],
            domain=config["domain"],
            force=True,
        )
        summaries.append(
            RagReindexDocumentOut(
                title=result.title,
                status=result.status,
                pages=result.pages,
                chunks=result.chunks,
                error_message=result.error_message,
            )
        )
    return RagReindexResponse(documents=summaries)
