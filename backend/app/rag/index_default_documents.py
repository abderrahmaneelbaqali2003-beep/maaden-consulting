"""Indexe les 2 documents par defaut de la V2 documentaire MAADEN Consulting.

Usage :
    python -m app.rag.index_default_documents

Cherche les fichiers dans `backend/data/documents/`, verifie s'ils sont deja
indexes (hash de fichier inchange), sinon extrait / chunk / embed / stocke dans
`rag.documents` et `rag.document_chunks`, puis affiche un resume.
"""

from pathlib import Path

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.rag.embeddings import get_embedding_provider
from app.rag.ingestion import DocumentIngestionService

DOCUMENTS_DIR = Path(__file__).resolve().parents[2] / "data" / "documents"

DEFAULT_DOCUMENTS = [
    {
        "file_name": "Synthese_documentaire_NM13201_MAADEN.pdf",
        "title": "Synthese documentaire NM 13 201",
        "document_type": "internal_summary",
        "standard_family": "road_lighting_13201",
        "domain": "eclairage_public",
    },
    {
        "file_name": "Guide_Normes_Eclairage_Public_MAADEN_Consulting_2026.pdf",
        "title": "Guide des normes pour l'eclairage public",
        "document_type": "normative_guide",
        "standard_family": "multi_standard",
        "domain": "eclairage_public",
    },
]


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    embedding_provider = get_embedding_provider(settings)
    service = DocumentIngestionService(db, settings, embedding_provider)

    print("MAADEN RAG indexing")
    print(
        f"Fournisseur d'embedding : {settings.embedding_provider} "
        f"({settings.embedding_model}, dim={settings.embedding_dimension})"
    )
    print()

    any_missing = False
    try:
        for index, config in enumerate(DEFAULT_DOCUMENTS, start=1):
            file_path = DOCUMENTS_DIR / config["file_name"]
            print(f"Document {index}:")
            print(config["title"])

            if not file_path.exists():
                any_missing = True
                print(f"Fichier manquant. Copiez-le dans : {file_path}")
                print("Status: missing")
                print()
                continue

            result = service.ingest(
                file_path=file_path,
                title=config["title"],
                document_type=config["document_type"],
                standard_family=config["standard_family"],
                domain=config["domain"],
            )

            print(f"Pages: {result.pages if result.pages else '-'}")
            print(f"Chunks: {result.chunks}")
            print(f"Status: {result.status}")
            if result.error_message:
                print(f"Erreur: {result.error_message}")
            print()
    finally:
        db.close()

    if any_missing:
        print(f"Certains documents sont manquants. Copiez-les dans {DOCUMENTS_DIR} puis relancez la commande.")


if __name__ == "__main__":
    main()
