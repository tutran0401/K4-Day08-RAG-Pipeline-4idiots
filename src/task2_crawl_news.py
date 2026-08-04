"""Task 2: crawl public help-center articles to auditable JSON records."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"
ARTICLE_URLS = [
    "https://help.shopee.vn/portal/4/article/77251",
    "https://help.shopee.vn/portal/4/article/79198",
    "https://help.shopee.vn/portal/4/article/79084",
    "https://help.shopee.vn/portal/4/article/79377",
    "https://help.shopee.vn/portal/4/article/79290",
]


def setup_directory() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def _html_to_text(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"</?(p|div|section|article|li|h[1-6]|br)[^>]*>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    import html as html_module
    return re.sub(r"\n{3,}", "\n\n", html_module.unescape(text)).strip()


async def crawl_article(url: str) -> dict:
    title, markdown = "Unknown", ""
    try:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            metadata = getattr(result, "metadata", {}) or {}
            title = metadata.get("title", title)
            markdown = str(getattr(result, "markdown", "") or "")
    except Exception:
        # Missing browser binaries are common in a fresh lab; use HTTP as a fallback.
        response = await asyncio.to_thread(
            requests.get, url, timeout=30, headers={"User-Agent": "Mozilla/5.0 RAG-Lab"}
        )
        response.raise_for_status()
        title_match = re.search(r"<title[^>]*>(.*?)</title>", response.text, re.I | re.S)
        title = _html_to_text(title_match.group(1)) if title_match else title
        markdown = _html_to_text(response.text)
    if len(markdown.strip()) < 200:
        raise ValueError(f"Page returned too little usable content: {url}")
    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now(timezone.utc).isoformat(),
        "content_markdown": markdown,
    }


async def crawl_all(urls: list[str] | None = None) -> list[Path]:
    setup_directory()
    selected = urls or ARTICLE_URLS
    records = await asyncio.gather(*(crawl_article(url) for url in selected))
    outputs = []
    for index, record in enumerate(records, 1):
        path = DATA_DIR / f"article_{index:02d}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(path)
    return outputs


if __name__ == "__main__":
    print(asyncio.run(crawl_all()))
