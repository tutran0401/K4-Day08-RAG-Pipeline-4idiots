"""Task 5: offline-first semantic search with optional model embeddings."""

from __future__ import annotations

import os
from functools import lru_cache

from .retrieval_utils import configure_utf8_stdout, cosine_similarity, hashing_embedding, keyword_overlap
from .task4_chunking_indexing import EMBEDDING_DIM, embedding_backend, load_or_build_index


@lru_cache(maxsize=2)
def _sentence_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)

def _query_embedding(query: str, dimensions: int) -> list[float]:
    if embedding_backend() == "sentence_transformer":
        model_name = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-m3")
        return _sentence_model(model_name).encode(query, normalize_embeddings=True).tolist()
    return hashing_embedding(query, dimensions)


def semantic_search(query: str, top_k: int = 10, metadata_filter: dict | None = None) -> list[dict]:
    """Return cosine-ranked chunks. Bilingual query expansion is built into the encoder."""
    if not isinstance(query, str) or not query.strip() or top_k <= 0:
        return []
    corpus = load_or_build_index()
    if metadata_filter:
        corpus = [
            item for item in corpus
            if all(item.get("metadata", {}).get(key) == value for key, value in metadata_filter.items())
        ]
    if not corpus:
        return []
    dimensions = len(corpus[0].get("embedding", [])) or EMBEDDING_DIM
    query_vector = _query_embedding(query, dimensions)
    results = []
    for item in corpus:
        cosine = max(0.0, cosine_similarity(query_vector, item.get("embedding", [])))
        # A small exact-term component improves acronyms/named entities without changing
        # the meaningful [0, 1] similarity scale used for fallback calibration.
        overlap = keyword_overlap(query, item.get("content", ""))
        score = min(1.0, 0.82 * cosine + 0.18 * overlap)
        results.append({
            "content": item.get("content", ""),
            "score": round(score, 6),
            "metadata": dict(item.get("metadata", {})),
            "id": item.get("id"),
        })
    results.sort(key=lambda result: (-result["score"], result.get("id") or ""))
    return results[:top_k]


if __name__ == "__main__":
    configure_utf8_stdout()
    for result in semantic_search("phương thức thanh toán", top_k=5):
        print(f"[{result['score']:.3f}] {result['content'][:100]}")
