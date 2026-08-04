"""Task 9: hybrid retrieval, RRF fusion, and structural fallback."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .retrieval_utils import configure_utf8_stdout
from .task4_chunking_indexing import load_or_build_index
from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_cross_encoder, rerank_rrf
from .task8_pageindex_vectorless import pageindex_search

# Calibrated against the bundled relevant and nonsense benchmark queries.
SCORE_THRESHOLD = 0.16
DEFAULT_TOP_K = 5


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
    metadata_filter: dict | None = None,
    retrieval_mode: str = "hybrid",
) -> list[dict]:
    if not isinstance(query, str) or not query.strip() or top_k <= 0:
        return []
    candidate_count = max(top_k * 3, top_k)
    # Build once before starting worker threads to avoid two first-run writers racing on
    # the persistent local index.
    load_or_build_index()

    if retrieval_mode == "dense":
        dense = semantic_search(query, candidate_count, metadata_filter)
        sparse = []
    elif retrieval_mode == "sparse":
        dense = []
        sparse = lexical_search(query, candidate_count, metadata_filter)
    elif retrieval_mode == "hybrid":
        with ThreadPoolExecutor(max_workers=2) as executor:
            dense_future = executor.submit(semantic_search, query, candidate_count, metadata_filter)
            sparse_future = executor.submit(lexical_search, query, candidate_count, metadata_filter)
            dense, sparse = dense_future.result(), sparse_future.result()
    else:
        raise ValueError("retrieval_mode must be 'hybrid', 'dense', or 'sparse'")

    # Fallback is intentionally decided using the original cosine score, never RRF.
    best_dense_score = float(dense[0]["score"]) if dense else 0.0
    if retrieval_mode != "sparse" and best_dense_score < score_threshold:
        fallback = pageindex_search(query, top_k)
        if fallback:
            return fallback

    if retrieval_mode == "hybrid":
        merged = rerank_rrf([dense, sparse], candidate_count)
    else:
        merged = [dict(item) for item in (dense or sparse)]

    final = rerank_cross_encoder(query, merged, top_k) if use_reranking else merged[:top_k]
    for item in final:
        item["source"] = "hybrid"
    return final[:top_k]


if __name__ == "__main__":
    configure_utf8_stdout()
    for result in retrieve("Shopee hỗ trợ phương thức thanh toán nào?", top_k=3):
        print(result["score"], result["source"], result["metadata"].get("source"))
