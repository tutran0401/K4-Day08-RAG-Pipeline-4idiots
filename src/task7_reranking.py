"""Task 7: cross-score, MMR, and Reciprocal Rank Fusion reranking."""

from __future__ import annotations

from .retrieval_utils import cosine_similarity, hashing_embedding, keyword_overlap


def rerank_cross_encoder(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Dependency-free relevance reranker; keeps the interface of a cross encoder.

    retrieval_score is min-max normalized across this candidate batch before blending,
    since its raw scale differs by retrieval_mode (RRF scores top out around 1/60,
    BM25 is unbounded, cosine is already ~[0, 1]) — clipping to [0, 1] instead would let
    RRF-fused candidates fall through with a near-zero contribution, silently collapsing
    the intended 0.7/0.3 blend to ~1.0/0.0 in hybrid mode.
    """
    if not candidates:
        return []
    raw_scores = [float(candidate.get("score", 0.0)) for candidate in candidates]
    lo, hi = min(raw_scores), max(raw_scores)
    spread = hi - lo
    rescored = []
    for candidate, original in zip(candidates, raw_scores):
        item = dict(candidate)
        overlap = keyword_overlap(query, item.get("content", ""))
        normalized = (original - lo) / spread if spread else 1.0
        item["retrieval_score"] = original
        item["score"] = round(0.7 * overlap + 0.3 * normalized, 6)
        rescored.append(item)
    rescored.sort(key=lambda item: item["score"], reverse=True)
    return rescored[:max(0, top_k)]


def rerank_mmr(
    query_embedding: list[float], candidates: list[dict], top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    if not 0 <= lambda_param <= 1:
        raise ValueError("lambda_param must be between 0 and 1")
    if not candidates or top_k <= 0:
        return []
    dimensions = len(query_embedding) or 768
    embeddings = [
        candidate.get("embedding") or hashing_embedding(candidate.get("content", ""), dimensions)
        for candidate in candidates
    ]
    selected: list[int] = []
    remaining = list(range(len(candidates)))
    while remaining and len(selected) < top_k:
        best_index, best_score = remaining[0], float("-inf")
        for index in remaining:
            relevance = cosine_similarity(query_embedding, embeddings[index])
            redundancy = max(
                (cosine_similarity(embeddings[index], embeddings[chosen]) for chosen in selected),
                default=0.0,
            )
            score = lambda_param * relevance - (1 - lambda_param) * redundancy
            if score > best_score:
                best_index, best_score = index, score
        item = dict(candidates[best_index])
        item["score"] = round(best_score, 6)
        candidates = list(candidates)
        selected.append(best_index)
        remaining.remove(best_index)
    # MMR order is intentional: each next document is selected conditioned on earlier ones.
    output = []
    for index in selected:
        item = dict(candidates[index])
        relevance = cosine_similarity(query_embedding, embeddings[index])
        item["score"] = round(relevance, 6)
        output.append(item)
    return output


def _document_key(item: dict) -> str:
    metadata = item.get("metadata", {})
    return str(item.get("id") or f"{metadata.get('source', '')}::{metadata.get('chunk_index', '')}::{item.get('content', '')}")


def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    if k < 0:
        raise ValueError("k must be non-negative")
    scores: dict[str, float] = {}
    documents: dict[str, dict] = {}
    for ranked_list in ranked_lists:
        seen = set()
        for rank, item in enumerate(ranked_list, 1):
            key = _document_key(item)
            if key in seen:
                continue
            seen.add(key)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            documents[key] = dict(item)
    ranked_keys = sorted(scores, key=lambda key: (-scores[key], key))
    results = []
    for key in ranked_keys[:max(0, top_k)]:
        item = documents[key]
        item["retrieval_score"] = item.get("score", 0.0)
        item["score"] = round(scores[key], 8)
        results.append(item)
    return results


def rerank(query: str, candidates: list[dict], top_k: int = 5, method: str = "rrf") -> list[dict]:
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    if method == "mmr":
        vector = hashing_embedding(query, 768)
        return rerank_mmr(vector, candidates, top_k)
    if method == "rrf":
        return rerank_rrf([candidates], top_k)
    raise ValueError(f"Unknown rerank method: {method}")
