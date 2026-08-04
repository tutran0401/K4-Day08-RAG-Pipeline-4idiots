"""Task 1: reproducibly collect official policy documents."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import requests

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}


def setup_directory() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def download_file(url: str, filename: str, timeout: int = 30) -> Path:
    """Download one public PDF/Word file with basic integrity checks."""
    target = setup_directory() / Path(filename).name
    if target.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("filename must end in .pdf, .doc, or .docx")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only HTTP(S) sources are supported")
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "RAG-Lab/1.0"})
    response.raise_for_status()
    if len(response.content) <= 1024:
        raise ValueError(f"downloaded file is unexpectedly small: {len(response.content)} bytes")
    target.write_bytes(response.content)
    return target


def inventory() -> list[dict]:
    """Return a transparent inventory for demo/review."""
    return [
        {"name": path.name, "bytes": path.stat().st_size}
        for path in sorted(setup_directory().iterdir())
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
    ]


if __name__ == "__main__":
    print(inventory())
