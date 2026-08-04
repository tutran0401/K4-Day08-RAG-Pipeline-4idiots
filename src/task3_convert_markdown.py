"""Task 3: convert landing-zone documents into normalized Markdown."""

from __future__ import annotations

import json
import re
from pathlib import Path

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _convert_office(path: Path) -> str:
    try:
        from markitdown import MarkItDown

        return MarkItDown().convert(str(path)).text_content
    except Exception as exc:
        if path.suffix.lower() == ".doc":
            # The bundled .doc snapshots are plain-text Word-compatible documents.
            return path.read_text(encoding="utf-8-sig", errors="replace")
        raise RuntimeError('Install "markitdown[pdf]" to convert PDF/DOCX inputs') from exc


def convert_legal_docs() -> list[Path]:
    source_dir, target_dir = LANDING_DIR / "legal", OUTPUT_DIR / "legal"
    target_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    if not source_dir.exists():
        return outputs
    for path in sorted(source_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        content = _convert_office(path).strip()
        if not content:
            continue
        target = target_dir / f"{path.stem}.md"
        target.write_text(content, encoding="utf-8")
        outputs.append(target)
    return outputs


def convert_news_articles() -> list[Path]:
    source_dir, target_dir = LANDING_DIR / "news", OUTPUT_DIR / "news"
    target_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    if not source_dir.exists():
        return outputs
    for path in sorted(source_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        content = data.get("content_markdown") or data.get("content") or ""
        header = (
            f"# {data.get('title', path.stem)}\n\n"
            f"**Source:** {data.get('url', 'N/A')}  \n"
            f"**Crawled:** {data.get('date_crawled', 'N/A')}  \n"
            f"**Customer role:** {data.get('customer_role', 'both')}\n\n"
        )
        target = target_dir / f"{path.stem}.md"
        target.write_text(header + re.sub(r"^# .+?\n+", "", content, count=1), encoding="utf-8")
        outputs.append(target)
    return outputs


def convert_all() -> list[Path]:
    return convert_legal_docs() + convert_news_articles()


if __name__ == "__main__":
    print(f"Converted {len(convert_all())} documents into {OUTPUT_DIR}")
