"""Pipeline d'ingestion des documents (V2 - 2 PDF MAADEN uniquement).

PDF -> validation -> SHA-256 -> extraction -> nettoyage -> chunking -> embeddings
-> insertion PostgreSQL -> status = indexed

Idempotent : un document deja indexe avec le meme hash de fichier n'est pas
reingere (sauf `force=True`). Chaque chunk est deduplique par hash de contenu.
En cas d'erreur, la transaction en cours est annulee et le document est marque
`failed` avec un message explicite (jamais `indexed` sans embeddings associes).
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import RagDocument, RagDocumentChunk
from app.rag.chunking import ChunkingStrategy, SectionAwareChunkingStrategy
from app.rag.embeddings import EmbeddingProvider
from app.rag.parsing import DocumentParser, PdfDocumentParser


@dataclass
class IngestionResult:
    document_id: int
    title: str
    status: str  # indexed / already_indexed / failed
    pages: int
    chunks: int
    error_message: str | None = None


def _clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _sha256_file(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DocumentIngestionService:
    """Ingere un PDF dans `rag.documents` / `rag.document_chunks`."""

    def __init__(
        self,
        db: Session,
        settings: Settings,
        embedding_provider: EmbeddingProvider,
        parser: DocumentParser | None = None,
        chunking_strategy: ChunkingStrategy | None = None,
    ):
        self.db = db
        self.settings = settings
        self.embedding_provider = embedding_provider
        self.parser = parser or PdfDocumentParser()
        self.chunking_strategy = chunking_strategy or SectionAwareChunkingStrategy(
            target_size=settings.rag_chunk_size, overlap=settings.rag_chunk_overlap
        )

    def ingest(
        self,
        file_path: Path,
        title: str,
        document_type: str,
        standard_family: str | None = None,
        domain: str | None = None,
        authority_level: str = "secondary",
        force: bool = False,
    ) -> IngestionResult:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Document introuvable : {file_path}. Copiez le fichier a cet emplacement avant l'indexation."
            )

        file_hash = _sha256_file(file_path)
        existing = self.db.query(RagDocument).filter(RagDocument.file_name == file_path.name).one_or_none()

        if existing and existing.embedding_status == "indexed" and existing.content_sha256 == file_hash and not force:
            chunk_count = (
                self.db.query(RagDocumentChunk).filter(RagDocumentChunk.document_id == existing.id).count()
            )
            return IngestionResult(
                document_id=existing.id, title=existing.title, status="already_indexed", pages=0, chunks=chunk_count
            )

        try:
            document = existing or RagDocument(file_name=file_path.name, title=title, document_type=document_type)
            document.title = title
            document.document_type = document_type
            document.standard_family = standard_family
            document.domain = domain
            document.language = "fr"
            document.authority_level = authority_level
            document.content_sha256 = file_hash
            document.embedding_status = "extracting"
            document.error_message = None
            self.db.add(document)
            self.db.flush()

            pages = self.parser.parse(file_path)
            for page in pages:
                page.text = _clean_text(page.text)

            parsed_chunks = self.chunking_strategy.chunk(pages)
            if not parsed_chunks:
                raise ValueError("Aucun passage exploitable extrait du document (texte vide ou non extractible).")

            document.embedding_status = "embedding"

            existing_hashes = {
                row.content_hash
                for row in self.db.query(RagDocumentChunk.content_hash).filter(
                    RagDocumentChunk.document_id == document.id
                )
            }
            new_items = [
                (chunk, _sha256_text(chunk.content))
                for chunk in parsed_chunks
                if _sha256_text(chunk.content) not in existing_hashes
            ]

            if new_items:
                embeddings = self.embedding_provider.embed_documents([chunk.content for chunk, _ in new_items])
                for (chunk, content_hash), embedding in zip(new_items, embeddings):
                    self.db.add(
                        RagDocumentChunk(
                            document_id=document.id,
                            chunk_index=chunk.chunk_index,
                            section_title=chunk.section_title,
                            content=chunk.content,
                            content_hash=content_hash,
                            page_number=chunk.page_number,
                            chunk_metadata={"source_file": file_path.name},
                            embedding=embedding,
                        )
                    )

            document.embedding_status = "indexed"
            self.db.commit()
            self.db.refresh(document)

            total_chunks = (
                self.db.query(RagDocumentChunk).filter(RagDocumentChunk.document_id == document.id).count()
            )
            return IngestionResult(
                document_id=document.id, title=document.title, status="indexed", pages=len(pages), chunks=total_chunks
            )
        except Exception as exc:
            self.db.rollback()
            failed_document = self.db.query(RagDocument).filter(RagDocument.file_name == file_path.name).one_or_none()
            if failed_document is None:
                failed_document = RagDocument(
                    file_name=file_path.name,
                    title=title,
                    document_type=document_type,
                    language="fr",
                    authority_level=authority_level,
                )
            failed_document.embedding_status = "failed"
            failed_document.error_message = str(exc)
            self.db.add(failed_document)
            self.db.commit()
            self.db.refresh(failed_document)
            return IngestionResult(
                document_id=failed_document.id,
                title=title,
                status="failed",
                pages=0,
                chunks=0,
                error_message=str(exc),
            )
