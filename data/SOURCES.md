# Data provenance and refresh notes

This repository contains small educational snapshots so the lab can be tested offline. They are not a replacement for the current marketplace terms shown to a user at transaction time.

| Dataset area | Public reference | Purpose |
|---|---|---|
| Returns/refunds | https://help.shopee.vn/portal/4/article/77251 | deadline, evidence and return workflow |
| Payment methods | https://help.shopee.vn/portal/4/article/79198 | payment choices, COD and payment security |
| Other help topics | https://help.shopee.vn/portal/4 | order tracking, cross-border shopping and account safety |
| Seller/privacy snapshot | public seller education and privacy/help-center pages | prohibited listing and privacy benchmark cases |

## Lineage

- `landing/legal/*.doc` are UTF-8, Word-compatible classroom snapshots with the source URL, customer role and review date embedded in the document.
- `landing/news/*.json` records preserve URL, title, collection timestamp, role and Markdown content.
- `standardized/**/*.md` is the normalized retrieval corpus.
- `index/chunks.json` is generated and ignored by Git; rebuild it with `python -m src.task4_chunking_indexing`.

To refresh news pages instead of using the bundled snapshots, review `ARTICLE_URLS` and run:

```powershell
python -m src.task2_crawl_news
python -m src.task3_convert_markdown
python -m src.task4_chunking_indexing
```

Some help-center pages are JavaScript-rendered. The crawler tries Crawl4AI first and falls back to HTTP only when the returned HTML contains enough usable content. Always inspect the JSON before committing it, remove navigation/cookie text and update the review date.
