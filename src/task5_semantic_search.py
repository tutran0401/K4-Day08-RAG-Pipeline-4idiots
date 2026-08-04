"""Task 5: offline-first semantic search with optional model embeddings."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

from .retrieval_utils import configure_utf8_stdout, cosine_similarity, hashing_embedding, keyword_overlap
from .task4_chunking_indexing import EMBEDDING_DIM, embedding_backend, load_or_build_index

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
HYDE_SYSTEM_PROMPT = (
    "Viết một đoạn ngắn (2-3 câu) như trích từ tài liệu chính sách thương mại điện tử, "
    "trả lời câu hỏi sau. Không cần chính xác tuyệt đối, chỉ cần đúng văn phong và từ khoá liên quan."
)


@lru_cache(maxsize=2)
def _sentence_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)

def _query_embedding(query: str, dimensions: int) -> list[float]:
    if embedding_backend() == "sentence_transformer":
        model_name = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-m3")
        return _sentence_model(model_name).encode(query, normalize_embeddings=True).tolist()
    return hashing_embedding(query, dimensions)


@lru_cache(maxsize=64)
def _generate_hypothetical_doc(query: str) -> str | None:
    """HyDE: ask the LLM for a short passage that would answer the query, to embed instead
    of the raw query. Opt-in via RAG_USE_HYDE=1; falls back to None (raw query) whenever the
    flag is off, no API key is configured, or the call fails, keeping search offline-first."""
    if os.getenv("RAG_USE_HYDE", "0") != "1":
        return None
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    api_key = openrouter_key or openai_key
    if not api_key:
        return None
    try:
        from openai import OpenAI

        base_url = os.getenv("OPENAI_BASE_URL") or ("https://openrouter.ai/api/v1" if openrouter_key else None)
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = OpenAI(**client_kwargs)
        model = LLM_MODEL.removeprefix("openai/") if openai_key and not openrouter_key else LLM_MODEL
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": HYDE_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.3,
            max_tokens=120,
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception:
        return None


def semantic_search(query: str, top_k: int = 10, metadata_filter: dict | None = None) -> list[dict]:
    """Return cosine-ranked chunks. Bilingual query expansion is built into the encoder.
    With RAG_USE_HYDE=1, the dense side embeds an LLM-generated hypothetical answer instead
    of the raw query; keyword overlap still matches the raw query so exact terms aren't lost
    to the hypothetical doc's phrasing."""
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
    hypothetical_doc = _generate_hypothetical_doc(query)
    query_vector = _query_embedding(hypothetical_doc or query, dimensions)
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
