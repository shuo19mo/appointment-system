"""FAISS-backed semantic retrieval for education knowledge documents."""

from dataclasses import dataclass
from threading import RLock

import faiss
import numpy as np


@dataclass(frozen=True)
class KnowledgeHit:
    id: int
    content: str
    category: str
    score: float


class VectorKnowledgeService:
    def __init__(self, repository, embedding_provider):
        if embedding_provider is None:
            raise ValueError("embedding_provider is required")
        self.repository = repository
        self.embedding_provider = embedding_provider
        self._signature: tuple[tuple[int, str], ...] = ()
        self._documents = []
        self._index = None
        self._lock = RLock()

    @property
    def ready(self) -> bool:
        return self.embedding_provider is not None

    def _rebuild_if_needed(self) -> None:
        documents = self.repository.list_knowledge(limit=1000)
        signature = tuple((item.id, item.updated_at.isoformat()) for item in documents)
        if self._index is not None and signature == self._signature:
            return
        self._documents = documents
        self._signature = signature
        if not documents:
            self._index = None
            return
        vectors = np.asarray(
            self.embedding_provider.embed_documents([item.content for item in documents]),
            dtype="float32",
        )
        if vectors.ndim != 2 or vectors.shape[0] != len(documents) or vectors.shape[1] == 0:
            raise ValueError("embedding provider returned an invalid document matrix")
        faiss.normalize_L2(vectors)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        self._index = index

    def search(self, query: str, *, top_k: int = 3, category: str | None = None) -> list[KnowledgeHit]:
        if top_k <= 0:
            return []
        with self._lock:
            self._rebuild_if_needed()
            if self._index is None:
                return []
            query_vector = np.asarray([self.embedding_provider.embed_query(query)], dtype="float32")
            if query_vector.shape[1] != self._index.d:
                raise ValueError("query embedding dimensions do not match the index")
            faiss.normalize_L2(query_vector)
            scores, positions = self._index.search(query_vector, len(self._documents))
            hits = []
            for score, position in zip(scores[0], positions[0]):
                if position < 0:
                    continue
                item = self._documents[int(position)]
                if category and item.category != category:
                    continue
                hits.append(KnowledgeHit(item.id, item.content, item.category, float(score)))
                if len(hits) == top_k:
                    break
            return hits

    def add_document(self, content: str, category: str, keywords: list[str] | None = None):
        return self.repository.add_knowledge(content, category, keywords)


KnowledgeService = VectorKnowledgeService
