"""Task 4: load, chunk, embed, and persist the e-commerce knowledge base.

The default hashing encoder is deterministic and works offline. Set
``RAG_EMBEDDING_BACKEND=sentence_transformer`` or the upstream-compatible
``EMBEDDING_PROVIDER=sentence_transformers`` alias to use a local transformer.
Changing providers or vector dimensions requires rebuilding the stored index.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .retrieval_utils import hashing_embedding, infer_customer_role

PROJECT_DIR = Path(__file__).parent.parent
STANDARDIZED_DIR = PROJECT_DIR / "data" / "standardized"
CHROMA_DIR = PROJECT_DIR / "chroma_db"
LOCAL_INDEX_PATH = PROJECT_DIR / "data" / "index" / "chunks.json"

# 700 chars usually keeps a policy clause intact; 100 chars preserves boundary context.
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100
CHUNKING_METHOD = "recursive"

# Offline-first deterministic multilingual encoder. The optional production backend is
# enabled with RAG_EMBEDDING_BACKEND=sentence_transformer and defaults to BAAI/bge-m3.
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "local-hashing-multilingual-v1")
EMBEDDING_DIM = int(os.getenv("RAG_EMBEDDING_DIM", "768"))
VECTOR_STORE = "chromadb"
COLLECTION_NAME = "ecommerce_support_docs"


def embedding_backend() -> str:
    """Return the normalized embedding backend configured by either env name."""
    provider = os.getenv("RAG_EMBEDDING_BACKEND") or os.getenv("EMBEDDING_PROVIDER") or "local"
    return "sentence_transformer" if provider.lower() == "sentence_transformers" else provider.lower()


def load_documents() -> list[dict]:
    documents: list[dict] = []
    if not STANDARDIZED_DIR.exists():
        return documents
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8-sig").strip()
        if not content:
            continue
        relative = path.relative_to(STANDARDIZED_DIR)
        doc_type = relative.parts[0] if len(relative.parts) > 1 else "unknown"
        documents.append({
            "content": content,
            "metadata": {
                "source": path.name,
                "path": relative.as_posix(),
                "type": doc_type,
                "customer_role": infer_customer_role(content),
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    if CHUNK_OVERLAP >= CHUNK_SIZE:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
    chunks: list[dict] = []
    for document in documents:
        text = str(document.get("content", "")).strip()
        start = index = 0
        while start < len(text):
            hard_end = min(start + CHUNK_SIZE, len(text))
            end = hard_end
            if hard_end < len(text):
                lower = start + CHUNK_SIZE // 2
                end = max(
                    text.rfind("\n\n", lower, hard_end),
                    text.rfind(". ", lower, hard_end),
                    text.rfind("\n", lower, hard_end),
                    text.rfind(" ", lower, hard_end),
                )
                if end <= start:
                    end = hard_end
                elif text[end:end + 2] == ". ":
                    end += 1
            content = text[start:end].strip()
            if content:
                metadata = dict(document.get("metadata", {}))
                metadata.update({"chunk_index": index, "char_start": start, "char_end": end})
                chunks.append({"content": content, "metadata": metadata})
                index += 1
            if end >= len(text):
                break
            next_start = end - CHUNK_OVERLAP
            start = next_start if next_start > start else end
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    if not chunks:
        return []
    texts = [str(chunk.get("content", "")) for chunk in chunks]
    if embedding_backend() == "sentence_transformer":
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-m3")
        matrix = SentenceTransformer(model_name).encode(texts, normalize_embeddings=True)
        vectors = [row.tolist() for row in matrix]
    else:
        vectors = [hashing_embedding(text, EMBEDDING_DIM) for text in texts]
    return [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]


def index_to_vectorstore(chunks: list[dict]) -> list[dict]:
    LOCAL_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    indexed = []
    for position, chunk in enumerate(chunks):
        item = dict(chunk)
        metadata = item.get("metadata", {})
        item["id"] = f"{metadata.get('source', 'doc')}::{metadata.get('chunk_index', position)}"
        indexed.append(item)
    LOCAL_INDEX_PATH.write_text(json.dumps(indexed, ensure_ascii=False), encoding="utf-8")

    if os.getenv("RAG_USE_CHROMA", "0") == "1" and indexed:
        import chromadb

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        collection = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
        collection.add(
            ids=[item["id"] for item in indexed],
            documents=[item["content"] for item in indexed],
            embeddings=[item["embedding"] for item in indexed],
            metadatas=[item["metadata"] for item in indexed],
        )
    return indexed


def load_or_build_index() -> list[dict]:
    sources = list(STANDARDIZED_DIR.rglob("*.md")) if STANDARDIZED_DIR.exists() else []
    newest_source = max((path.stat().st_mtime for path in sources), default=0)
    if LOCAL_INDEX_PATH.exists() and LOCAL_INDEX_PATH.stat().st_mtime >= newest_source:
        try:
            return json.loads(LOCAL_INDEX_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return index_to_vectorstore(embed_chunks(chunk_documents(load_documents())))


def run_pipeline() -> list[dict]:
    documents = load_documents()
    chunks = embed_chunks(chunk_documents(documents))
    indexed = index_to_vectorstore(chunks)
    print(f"Loaded {len(documents)} documents; indexed {len(indexed)} chunks at {LOCAL_INDEX_PATH}")
    return indexed


if __name__ == "__main__":
    run_pipeline()
