"""Task 6: BM25 lexical retrieval implemented without mandatory dependencies."""

from __future__ import annotations

import math
import os
from collections import Counter

from .retrieval_utils import configure_utf8_stdout, tokenize
from .task4_chunking_indexing import load_or_build_index

CORPUS: list[dict] = []


class BM25Index:
    def __init__(self, corpus: list[dict], k1: float = 1.5, b: float = 0.75):
        self.corpus = corpus
        self.k1, self.b = k1, b
        self.documents = [tokenize(item.get("content", ""), expand=True) for item in corpus]
        self.term_frequencies = [Counter(tokens) for tokens in self.documents]
        self.lengths = [len(tokens) for tokens in self.documents]
        self.avg_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        document_frequency: Counter = Counter()
        for tokens in self.documents:
            document_frequency.update(set(tokens))
        total = len(self.documents)
        self.idf = {
            term: math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        scores = []
        for frequencies, length in zip(self.term_frequencies, self.lengths):
            score = 0.0
            for term in query_tokens:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                norm = frequency + self.k1 * (1 - self.b + self.b * length / (self.avg_length or 1))
                score += self.idf.get(term, 0.0) * frequency * (self.k1 + 1) / norm
            scores.append(score)
        return scores


class TFIDFIndex:
    """Classic TF-IDF cosine index, provided as the lexical-search bonus backend."""

    def __init__(self, corpus: list[dict]):
        self.corpus = corpus
        self.term_frequencies = [Counter(tokenize(item.get("content", ""), expand=True)) for item in corpus]
        frequency: Counter = Counter()
        for terms in self.term_frequencies:
            frequency.update(terms.keys())
        total = len(corpus)
        self.idf = {term: math.log((total + 1) / (count + 1)) + 1 for term, count in frequency.items()}
        self.vectors = [self._vector(terms) for terms in self.term_frequencies]

    def _vector(self, frequencies: Counter) -> dict[str, float]:
        total = sum(frequencies.values()) or 1
        return {term: count / total * self.idf.get(term, 0.0) for term, count in frequencies.items()}

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        dot = sum(value * right.get(term, 0.0) for term, value in left.items())
        norm = math.sqrt(sum(value * value for value in left.values()) * sum(value * value for value in right.values()))
        return dot / norm if norm else 0.0

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        query_vector = self._vector(Counter(query_tokens))
        return [self._cosine(query_vector, vector) for vector in self.vectors]


def build_bm25_index(corpus: list[dict]) -> BM25Index:
    return BM25Index(list(corpus))


def build_tfidf_index(corpus: list[dict]) -> TFIDFIndex:
    return TFIDFIndex(list(corpus))


def lexical_search(query: str, top_k: int = 10, metadata_filter: dict | None = None) -> list[dict]:
    if not isinstance(query, str) or not query.strip() or top_k <= 0:
        return []
    global CORPUS
    CORPUS = load_or_build_index()
    corpus = CORPUS
    if metadata_filter:
        corpus = [
            item for item in corpus
            if all(item.get("metadata", {}).get(key) == value for key, value in metadata_filter.items())
        ]
    if not corpus:
        return []
    method = os.getenv("LEXICAL_METHOD", "bm25").lower()
    if method not in {"bm25", "tfidf"}:
        raise ValueError("LEXICAL_METHOD must be 'bm25' or 'tfidf'")
    index = build_tfidf_index(corpus) if method == "tfidf" else build_bm25_index(corpus)
    scores = index.get_scores(tokenize(query, expand=True))
    ranked = sorted(enumerate(scores), key=lambda pair: (-pair[1], pair[0]))
    results = []
    for position, score in ranked:
        if score <= 0:
            continue
        item = corpus[position]
        results.append({
            "content": item.get("content", ""),
            "score": round(float(score), 6),
            "metadata": dict(item.get("metadata", {})),
            "id": item.get("id"),
        })
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    configure_utf8_stdout()
    for result in lexical_search("phương thức thanh toán", top_k=5):
        print(f"[{result['score']:.3f}] {result['content'][:100]}")
