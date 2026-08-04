"""Task 10: grounded generation with citations and an offline extractive fallback."""

from __future__ import annotations

import os
import re
import math
from collections import Counter

from dotenv import load_dotenv

from .retrieval_utils import configure_utf8_stdout, keyword_overlap, normalize_text, tokenize
from .task9_retrieval_pipeline import retrieve

load_dotenv()
TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.2
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

SYSTEM_PROMPT = """Bạn là trợ lý chính sách thương mại điện tử. Chỉ dùng context được cung cấp.
Mỗi khẳng định phải có citation [tên nguồn]. Nếu context không đủ, trả lời đúng câu:
\"Tôi không thể xác minh thông tin này từ nguồn hiện có.\" Trả lời bằng tiếng Việt, ngắn gọn."""


def expand_follow_up_query(query: str, conversation_history: list[dict] | None = None) -> str:
    """Resolve short/pronominal follow-ups using the latest user turn (query expansion)."""
    history = conversation_history or []
    tokens = tokenize(query)
    normalized = " ".join(tokens)
    follow_up_markers = ("con", "do", "no", "vay", "the", "truong hop nay", "what about", "that")
    token_set = set(tokens)
    has_marker = any(
        marker in normalized if " " in marker else marker in token_set
        for marker in follow_up_markers
    )
    is_follow_up = len(tokens) <= 7 or has_marker
    if not is_follow_up:
        return query
    previous = next(
        (item.get("content", "") for item in reversed(history) if item.get("role") == "user" and item.get("content")),
        "",
    )
    return f"{previous}\nCâu hỏi tiếp theo: {query}" if previous and previous != query else query


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    if len(chunks) <= 2:
        return list(chunks)
    return list(chunks[::2]) + list(chunks[1::2])[::-1]


def format_context(chunks: list[dict]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata") or {}
        source = metadata.get("source", f"source-{index}")
        doc_type = metadata.get("type", "unknown")
        section = metadata.get("section")
        label = f"Document {index} | Source: {source} | Type: {doc_type}"
        if section:
            label += f" | Section: {section}"
        parts.append(f"[{label}]\n{chunk.get('content', '').strip()}")
    return "\n\n---\n\n".join(parts)


def _extractive_answer(query: str, chunks: list[dict]) -> str:
    candidates = []
    original_query_terms = set(tokenize(query, expand=False))
    expanded_query_terms = set(tokenize(query, expand=True))
    normalized_query = normalize_text(query)
    asks_for_list = (
        ("nhung" in original_query_terms and "nao" in original_query_terms)
        or "gi" in original_query_terms
        or bool(original_query_terms & {"what", "which"})
    )
    explicit_list = (
        ("nhung" in original_query_terms and "nao" in original_query_terms)
        or bool(original_query_terms & {"what", "which"})
    )
    asks_for_time = any(marker in normalized_query for marker in ("bao lau", "thoi han", "deadline", "how long"))
    primary_source = ((chunks[0].get("metadata") or {}).get("source") if chunks else None)
    for chunk_rank, chunk in enumerate(chunks):
        source = (chunk.get("metadata") or {}).get("source", "nguồn không xác định")
        # The retriever's top source is the evidence anchor. Restricting extraction to it
        # prevents a generic sentence from a lower-ranked policy from hijacking the answer.
        if primary_source and source != primary_source:
            continue
        lines = []
        for line in chunk.get("content", "").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ">")):
                continue
            if re.match(r"^\*\*(source|customer role|dataset review|crawled):", stripped, re.I):
                continue
            lines.append(stripped)
        clean = " ".join(lines)
        clean = re.sub(r"[*_`]", "", clean)
        for sentence in re.split(r"(?<=[.!?])\s+|\s+(?=[-*]\s)", clean):
            sentence = re.sub(r"^(?:[-*]\s*|\d+[.)]\s*)", "", sentence.strip())
            if len(sentence) < 25 or (sentence and sentence[0].islower()):
                continue
            sentence_terms = set(tokenize(sentence, expand=True))
            candidates.append({
                "sentence": sentence,
                "source": source,
                "terms": sentence_terms,
                "rank": chunk_rank,
            })

    document_frequency = Counter()
    for candidate in candidates:
        document_frequency.update(candidate["terms"])
    total = len(candidates)
    scored = []
    for candidate in candidates:
        original_matches = original_query_terms & candidate["terms"]
        expanded_matches = expanded_query_terms & candidate["terms"]
        score = sum(math.log(1 + total / (1 + document_frequency[term])) for term in original_matches)
        score += 0.35 * sum(
            math.log(1 + total / (1 + document_frequency[term]))
            for term in expanded_matches - original_matches
        )
        score /= math.sqrt(max(len(candidate["terms"]), 1))
        score += 0.06 / (candidate["rank"] + 1)
        if asks_for_list and candidate["sentence"].count(",") >= 2:
            score += 0.45
        if asks_for_time and re.search(r"\b\d+\s*(ngay|gio|day|hour)", normalize_text(candidate["sentence"])):
            score += 2.0
        if original_matches or expanded_matches:
            scored.append((score, candidate["sentence"], candidate["source"]))
    scored.sort(key=lambda item: (-item[0], len(item[1])))
    selected, seen = [], set()
    best_score = scored[0][0] if scored else 0.0
    for score, sentence, source in scored:
        cutoff = 0.35 if asks_for_time else 0.62
        if selected and score < best_score * cutoff:
            break
        key = sentence.lower()
        if key in seen or any(keyword_overlap(sentence, old) > 0.82 for old in seen):
            continue
        seen.add(key)
        selected.append(f"{sentence} [{source}]")
        if (explicit_list and sentence.count(",") >= 2) or len(selected) == 2:
            break
    if not selected:
        return "Tôi không thể xác minh thông tin này từ nguồn hiện có."
    return " ".join(selected)


def generate_with_citation(
    query: str,
    top_k: int = TOP_K,
    conversation_history: list[dict] | None = None,
) -> dict:
    effective_query = expand_follow_up_query(query, conversation_history)
    chunks = retrieve(effective_query, top_k=top_k)
    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    answer = ""
    used_llm = False
    generation_warning = None
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    api_key = openrouter_key or openai_key
    if api_key and context:
        try:
            from openai import OpenAI

            base_url = os.getenv("OPENAI_BASE_URL") or ("https://openrouter.ai/api/v1" if openrouter_key else None)
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            client = OpenAI(**client_kwargs)
            history = (conversation_history or [])[-4:]
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(
                {"role": item.get("role", "user"), "content": item.get("content", "")}
                for item in history if item.get("role") in {"user", "assistant"}
            )
            messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"})
            model = LLM_MODEL.removeprefix("openai/") if openai_key and not openrouter_key else LLM_MODEL
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=TEMPERATURE, top_p=TOP_P
            )
            answer = response.choices[0].message.content or ""
            if answer and not re.search(r"\[[^\]]+\]", answer):
                generation_warning = "LLM response had no citation; used grounded extractive fallback."
                answer = ""
            else:
                used_llm = True
        except Exception as exc:
            generation_warning = f"LLM unavailable ({type(exc).__name__}); used extractive fallback."
    if not answer:
        answer = _extractive_answer(effective_query, chunks)
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": chunks[0].get("source", "none") if chunks else "none",
        "context": context,
        "effective_query": effective_query,
        "generation_mode": "llm" if used_llm else "extractive",
        "generation_warning": generation_warning,
    }


if __name__ == "__main__":
    configure_utf8_stdout()
    result = generate_with_citation("Shopee hỗ trợ phương thức thanh toán nào?")
    print(result["answer"])
    print(f"Generation mode: {result['generation_mode']}")
    if result.get("generation_warning"):
        print(result["generation_warning"])
