"""Recherche documentaire : semantique, plein texte (PostgreSQL), fusion hybride.

Le corpus est volontairement petit (2 documents, quelques dizaines de passages)
pour cette V2 : les embeddings sont stockes en JSONB (cf.
`app.database.models.rag`) et la similarite cosinus est calculee cote Python
dans `VectorSearchService`, sans extension native (`pgvector`) a installer.
Si le corpus grossit significativement, `VectorSearchService.search()` est le
seul endroit a adapter (ex: bascule vers un index vectoriel natif) : son API
(`SearchResult`, `SearchFilters`) resterait inchangee pour les appelants.
"""

import math
from dataclasses import dataclass, field

from sqlalchemy.orm import Query, Session

from app.database.models import RagDocument, RagDocumentChunk
from app.rag.embeddings import EmbeddingProvider


@dataclass
class SearchFilters:
    document_type: str | None = None
    standard_family: str | None = None
    domain: str | None = None
    language: str | None = None
    authority_level: str | None = None


@dataclass
class SearchResult:
    chunk_id: int
    document_id: int
    document_title: str
    section_title: str | None
    page_number: int | None
    content: str
    similarity_score: float
    metadata: dict = field(default_factory=dict)


def _apply_filters(query: Query, filters: SearchFilters | None) -> Query:
    if filters is None:
        return query
    if filters.document_type:
        query = query.filter(RagDocument.document_type == filters.document_type)
    if filters.standard_family:
        query = query.filter(RagDocument.standard_family == filters.standard_family)
    if filters.domain:
        query = query.filter(RagDocument.domain == filters.domain)
    if filters.language:
        query = query.filter(RagDocument.language == filters.language)
    if filters.authority_level:
        query = query.filter(RagDocument.authority_level == filters.authority_level)
    return query


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorSearchService:
    """Recherche par similarite cosinus, calculee en Python (embeddings stockes en JSONB).

    Charge les passages actifs (filtres eventuels appliques cote SQL), calcule
    la similarite avec la requete en memoire, puis trie. Adapte a un corpus de
    quelques dizaines/centaines de passages (V2 : 2 documents) ; au-dela, un
    index vectoriel natif (pgvector) deviendrait pertinent.
    """

    def __init__(self, db: Session, embedding_provider: EmbeddingProvider):
        self.db = db
        self.embedding_provider = embedding_provider

    def search(self, query: str, limit: int = 5, filters: SearchFilters | None = None) -> list[SearchResult]:
        query_vector = self.embedding_provider.embed_query(query)

        db_query = (
            self.db.query(RagDocumentChunk, RagDocument)
            .join(RagDocument, RagDocumentChunk.document_id == RagDocument.id)
            .filter(RagDocument.active.is_(True))
            .filter(RagDocumentChunk.embedding.isnot(None))
        )
        db_query = _apply_filters(db_query, filters)
        rows = db_query.all()

        scored = [
            (chunk, document, _cosine_similarity(query_vector, chunk.embedding)) for chunk, document in rows
        ]
        scored.sort(key=lambda item: item[2], reverse=True)

        return [
            SearchResult(
                chunk_id=chunk.id,
                document_id=document.id,
                document_title=document.title,
                section_title=chunk.section_title,
                page_number=chunk.page_number,
                content=chunk.content,
                similarity_score=round(score, 4),
                metadata=chunk.chunk_metadata or {},
            )
            for chunk, document, score in scored[:limit]
        ]


class TextSearchService:
    """Recherche plein texte PostgreSQL (`to_tsvector('french', content)`).

    Construit une requete en OU logique entre les mots de `query` (chunk trouve
    s'il contient au moins un des mots, `ts_rank` favorisant naturellement les
    chunks qui en contiennent plusieurs) plutot qu'un ET strict
    (`plainto_tsquery` par defaut) : une requete a 4-5 mots n'a alors quasiment
    jamais de resultat des lors qu'aucun passage ne contient les 4-5 a la fois.
    """

    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, limit: int = 5, filters: SearchFilters | None = None) -> list[SearchResult]:
        import re

        from sqlalchemy import func

        words = re.findall(r"\w+", query, flags=re.UNICODE)
        if not words:
            return []
        tsquery = func.to_tsquery("french", " | ".join(words))
        tsvector = func.to_tsvector("french", RagDocumentChunk.content)
        rank = func.ts_rank(tsvector, tsquery).label("rank")

        db_query = (
            self.db.query(RagDocumentChunk, RagDocument, rank)
            .join(RagDocument, RagDocumentChunk.document_id == RagDocument.id)
            .filter(RagDocument.active.is_(True))
            .filter(tsvector.op("@@")(tsquery))
        )
        db_query = _apply_filters(db_query, filters)
        rows = db_query.order_by(rank.desc()).limit(limit).all()

        return [
            SearchResult(
                chunk_id=chunk.id,
                document_id=document.id,
                document_title=document.title,
                section_title=chunk.section_title,
                page_number=chunk.page_number,
                content=chunk.content,
                similarity_score=round(float(rank_value), 4),
                metadata=chunk.chunk_metadata or {},
            )
            for chunk, document, rank_value in rows
        ]


class HybridRetrievalService:
    """Fusionne recherche vectorielle et recherche plein texte (Reciprocal Rank Fusion).

    RRF : score(chunk) = somme, sur chaque liste ou le chunk apparait, de
    `weight / (rrf_k + rang_dans_la_liste)`. Poids et `rrf_k` sont configurables
    au lieu de melanger arbitrairement des scores de nature differente
    (distance cosinus vs `ts_rank`).
    """

    def __init__(
        self,
        vector_search: VectorSearchService,
        text_search: TextSearchService,
        rrf_k: int = 60,
        vector_weight: float = 1.0,
        text_weight: float = 1.0,
        min_vector_score: float = 0.0,
    ):
        self.vector_search = vector_search
        self.text_search = text_search
        self.rrf_k = rrf_k
        self.vector_weight = vector_weight
        self.text_weight = text_weight
        # Seuil applique uniquement au cote vectoriel (similarite cosinus, echelle
        # 0-1 interpretable) : le score fusionne RRF n'est lui-meme pas comparable
        # a un seuil de similarite absolu, donc jamais filtre de cette maniere.
        self.min_vector_score = min_vector_score

    def search(
        self,
        query: str,
        limit: int = 5,
        filters: SearchFilters | None = None,
        candidate_pool: int = 20,
    ) -> list[SearchResult]:
        vector_results = [
            r
            for r in self.vector_search.search(query, limit=candidate_pool, filters=filters)
            if r.similarity_score >= self.min_vector_score
        ]
        text_results = self.text_search.search(query, limit=candidate_pool, filters=filters)

        fused_scores: dict[int, float] = {}
        result_by_id: dict[int, SearchResult] = {}

        for rank, result in enumerate(vector_results, start=1):
            fused_scores[result.chunk_id] = fused_scores.get(result.chunk_id, 0.0) + self.vector_weight / (
                self.rrf_k + rank
            )
            result_by_id[result.chunk_id] = result

        for rank, result in enumerate(text_results, start=1):
            fused_scores[result.chunk_id] = fused_scores.get(result.chunk_id, 0.0) + self.text_weight / (
                self.rrf_k + rank
            )
            result_by_id.setdefault(result.chunk_id, result)

        ranked_ids = sorted(fused_scores, key=lambda chunk_id: fused_scores[chunk_id], reverse=True)[:limit]

        results = []
        for chunk_id in ranked_ids:
            result = result_by_id[chunk_id]
            result.similarity_score = round(fused_scores[chunk_id], 4)
            results.append(result)
        return results
