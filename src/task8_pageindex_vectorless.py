"""Task 8: structural, vectorless fallback inspired by PageIndex.

The local implementation searches the document/heading tree and therefore remains usable
during an offline demo. A manifest makes later PageIndex API uploads reproducible.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from .retrieval_utils import configure_utf8_stdout, normalize_text, tokenize

load_dotenv()
PROJECT_DIR = Path(__file__).parent.parent
STANDARDIZED_DIR = PROJECT_DIR / "data" / "standardized"
MANIFEST_PATH = PROJECT_DIR / "data" / "pageindex_manifest.json"
PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
PAGEINDEX_API_URL = "https://api.pageindex.ai"


def _sections(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    heading = path.stem
    buffer: list[str] = []
    sections: list[dict] = []

    def flush():
        content = "\n".join(buffer).strip()
        if content:
            sections.append({"title": heading, "content": content})

    for line in text.splitlines():
        if re.match(r"^#{1,4}\s+", line):
            flush()
            buffer.clear()
            heading = re.sub(r"^#{1,4}\s+", "", line).strip()
        else:
            buffer.append(line)
    flush()
    return sections


def upload_documents() -> list[dict]:
    """Create a local manifest and optionally upload landing-zone PDFs to PageIndex."""
    manifest = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        relative = path.relative_to(STANDARDIZED_DIR).as_posix()
        manifest.append({
            "source": path.name,
            "path": relative,
            "sections": len(_sections(path)),
            "status": "indexed_locally",
        })
    # Current official SDK accepts PDFs for document processing. Remote mode is explicit
    # because uploads change external state and can consume quota:
    # https://docs.pageindex.ai/getting-started
    if PAGEINDEX_API_KEY and os.getenv("PAGEINDEX_REMOTE", "0") == "1":
        for pdf_path in sorted((PROJECT_DIR / "data" / "landing" / "legal").glob("*.pdf")):
            with pdf_path.open("rb") as file_handle:
                response = requests.post(
                    f"{PAGEINDEX_API_URL}/doc/",
                    headers={"api_key": PAGEINDEX_API_KEY},
                    files={"file": (pdf_path.name, file_handle, "application/pdf")},
                    timeout=120,
                )
            response.raise_for_status()
            manifest.append({
                "source": pdf_path.name,
                "path": str(pdf_path.relative_to(PROJECT_DIR)),
                "doc_id": response.json().get("doc_id"),
                "status": "submitted_remote",
            })
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _flatten_relevant_contents(value) -> list[dict]:
    if isinstance(value, dict):
        if value.get("relevant_content"):
            return [value]
        output = []
        for nested in value.values():
            output.extend(_flatten_relevant_contents(nested))
        return output
    if isinstance(value, list):
        output = []
        for nested in value:
            output.extend(_flatten_relevant_contents(nested))
        return output
    return []


def _remote_search(query: str, top_k: int) -> list[dict]:
    if not (PAGEINDEX_API_KEY and os.getenv("PAGEINDEX_REMOTE", "0") == "1" and MANIFEST_PATH.exists()):
        return []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    documents = [item for item in manifest if item.get("doc_id")]
    results = []
    for document in documents:
        response = requests.post(
            f"{PAGEINDEX_API_URL}/retrieval/",
            headers={"api_key": PAGEINDEX_API_KEY},
            json={"doc_id": document["doc_id"], "query": query, "thinking": False},
            timeout=30,
        )
        response.raise_for_status()
        retrieval_id = response.json().get("retrieval_id")
        if not retrieval_id:
            continue
        payload = {}
        for _ in range(15):
            status = requests.get(
                f"{PAGEINDEX_API_URL}/retrieval/{retrieval_id}/",
                headers={"api_key": PAGEINDEX_API_KEY},
                timeout=30,
            )
            status.raise_for_status()
            payload = status.json()
            if payload.get("status") in {"completed", "failed"}:
                break
            time.sleep(1)
        for node in payload.get("retrieved_nodes", []):
            for content in _flatten_relevant_contents(node.get("relevant_contents", [])):
                text = content.get("relevant_content", "").strip()
                if text:
                    results.append({
                        "content": text,
                        "score": round(1.0 / (1 + len(results)), 6),
                        "metadata": {
                            "source": document.get("source", document["doc_id"]),
                            "section": content.get("section_title") or node.get("title"),
                            "page_index": content.get("page_index"),
                            "doc_id": document["doc_id"],
                        },
                        "source": "pageindex",
                    })
    return results[:top_k]


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    if not isinstance(query, str) or not query.strip() or top_k <= 0:
        return []
    try:
        remote_results = _remote_search(query, top_k)
        if remote_results:
            return remote_results
    except (requests.RequestException, OSError, ValueError, json.JSONDecodeError):
        # The local structural index is the availability fallback, not a silent failure.
        pass
    stopwords = {"la", "va", "co", "the", "khi", "cho", "cua", "toi", "mot", "nhung", "gi", "nao"}
    query_terms = {term for term in tokenize(query, expand=True) if len(term) > 2 and term not in stopwords}
    if not query_terms:
        return []
    candidates = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        relative = path.relative_to(STANDARDIZED_DIR)
        doc_type = relative.parts[0] if len(relative.parts) > 1 else "unknown"
        for section_index, section in enumerate(_sections(path)):
            title_terms = set(tokenize(section["title"], expand=True))
            content_terms = set(tokenize(section["content"], expand=True))
            title_overlap = len(query_terms & title_terms) / len(query_terms)
            content_overlap = len(query_terms & content_terms) / len(query_terms)
            phrase_bonus = 0.15 if normalize_text(query) in normalize_text(section["content"]) else 0.0
            score = min(1.0, 0.45 * title_overlap + 0.55 * content_overlap + phrase_bonus)
            if score <= 0:
                continue
            candidates.append({
                "content": section["content"],
                "score": round(score, 6),
                "metadata": {
                    "source": path.name,
                    "path": relative.as_posix(),
                    "type": doc_type,
                    "section": section["title"],
                    "section_index": section_index,
                    "matched_terms": sorted(query_terms & set(tokenize(section["content"], expand=True))),
                },
                "source": "pageindex",
            })
    candidates.sort(key=lambda item: (-item["score"], item["metadata"]["path"], item["metadata"]["section_index"]))
    return candidates[:top_k]


if __name__ == "__main__":
    configure_utf8_stdout()
    upload_documents()
    print(pageindex_search("phương thức thanh toán", top_k=3))
