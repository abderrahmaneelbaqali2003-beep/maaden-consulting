"""Abstraction d'embedding.

Aucune API payante, aucune cle, aucun appel reseau necessaire : le fournisseur par
defaut (`embedding_provider=mock`) ne depend d'aucune bibliotheque lourde.
`LocalSentenceTransformerProvider` charge un modele Sentence Transformers
multilingue local, uniquement lorsqu'il est explicitement selectionne.
"""

import hashlib
import struct
from abc import ABC, abstractmethod

from app.core.config import Settings


class EmbeddingProvider(ABC):
    dimension: int

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...


class LocalSentenceTransformerProvider(EmbeddingProvider):
    """Modele Sentence Transformers multilingue local (aucun appel externe a l'inference).

    Le modele est charge paresseusement (import de `sentence-transformers` + poids
    HuggingFace mis en cache localement au premier appel) afin de ne jamais imposer
    cette dependance lourde lorsque `embedding_provider=mock` est utilise.
    """

    def __init__(self, model_name: str, dimension: int):
        self._model_name = model_name
        self.dimension = dimension
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # import paresseux

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        vectors = model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class MockEmbeddingProvider(EmbeddingProvider):
    """Embedding deterministe sans dependance externe (tests, environnements sans modele installe).

    Projette un hachage SHA-256 du texte sur un vecteur de la dimension configuree,
    puis normalise. Ne capture aucune similarite semantique reelle : permet toutefois
    d'exercer l'intégralite du pipeline (stockage JSONB, recherche, fusion hybride)
    sans dependre de `sentence-transformers`/`torch`.
    """

    def __init__(self, dimension: int):
        self.dimension = dimension

    def _vector_for(self, text: str) -> list[float]:
        seed = text.strip().lower().encode("utf-8")
        values: list[float] = []
        counter = 0
        while len(values) < self.dimension:
            digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            values.extend(struct.unpack(">16h", digest[:32]))
            counter += 1
        values = values[: self.dimension]
        norm = sum(v * v for v in values) ** 0.5 or 1.0
        return [v / norm for v in values]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector_for(text)


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Fabrique selon `settings.embedding_provider` ('mock' ou 'sentence_transformer')."""
    if settings.embedding_provider == "sentence_transformer":
        return LocalSentenceTransformerProvider(settings.embedding_model, settings.embedding_dimension)
    return MockEmbeddingProvider(settings.embedding_dimension)
