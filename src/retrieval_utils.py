"""Dependency-light utilities shared by retrieval modules."""

from __future__ import annotations

import hashlib
import math
import re
import sys
import unicodedata
from collections import Counter

SYNONYMS = (
    ("payment", "pay", "thanh toan", "chi tra", "checkout"),
    ("method", "methods", "phuong thuc", "hinh thuc"),
    ("return", "returns", "tra hang", "doi tra"),
    ("refund", "refunds", "hoan tien", "boi hoan"),
    ("seller", "nguoi ban", "nha ban hang"),
    ("buyer", "customer", "nguoi mua", "khach hang"),
    ("privacy", "bao mat", "quyen rieng tu", "du lieu ca nhan"),
    ("shipping", "delivery", "giao hang", "van chuyen"),
    ("order", "don hang"),
    ("evidence", "proof", "bang chung", "chung tu"),
    ("prohibited", "banned", "cam", "khong duoc dang ban"),
    ("tracking", "theo doi", "tra cuu"),
    ("cancel", "cancellation", "huy", "huy don"),
    ("available", "availability", "kha dung", "xuat hien", "hien thi"),
    ("enforcement", "penalty", "xu ly", "go bai", "han che", "dinh chi", "vi pham"),
)


def configure_utf8_stdout() -> None:
    """Make Vietnamese CLI output reliable on legacy Windows code pages."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFD", str(text).lower())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def tokenize(text: str, expand: bool = False) -> list[str]:
    normalized = normalize_text(text)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    if not expand:
        return tokens
    expanded = list(tokens)
    padded = f" {normalized} "
    for group in SYNONYMS:
        terms = [normalize_text(item) for item in group]
        if any(f" {term} " in padded for term in terms):
            for term in terms:
                expanded.extend(term.split())
    return expanded


def hashing_embedding(text: str, dimensions: int = 768) -> list[float]:
    words = tokenize(text, expand=True)
    features = [f"w:{word}" for word in words]
    features += [f"b:{a}_{b}" for a, b in zip(words, words[1:])]
    vector = [0.0] * dimensions
    for feature, count in Counter(features).items():
        value = int.from_bytes(hashlib.blake2b(feature.encode(), digest_size=8).digest(), "little")
        vector[value % dimensions] += (-1.0 if value & (1 << 63) else 1.0) * (1 + math.log(count))
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def cosine_similarity(left, right) -> float:
    a, b = list(left), list(right)
    if not a or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    return max(-1.0, min(1.0, dot / norm)) if norm else 0.0


def keyword_overlap(query: str, document: str) -> float:
    query_terms = set(tokenize(query, expand=True))
    document_terms = set(tokenize(document, expand=True))
    return len(query_terms & document_terms) / len(query_terms) if query_terms else 0.0


def infer_customer_role(text: str) -> str:
    normalized = normalize_text(text)
    seller = any(term in normalized for term in ("seller", "nguoi ban", "dang ban", "listing"))
    buyer = any(term in normalized for term in ("buyer", "nguoi mua", "thanh toan", "tra hang", "don hang"))
    if seller and not buyer:
        return "seller"
    if buyer and not seller:
        return "buyer"
    return "both"
