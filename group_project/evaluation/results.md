# RAG Evaluation Results

**Generated from:** 16 golden cases
**Evaluator:** RAGAS-compatible deterministic CI proxy (no LLM judge)

> The default report uses deterministic support metrics for reproducible offline CI. Set `RAGAS_USE_LLM=1` for the official RAGAS LLM judge; do not compare the two score types directly.

## Overall Scores

| Metric | Config A: hybrid + rerank | Config B: dense-only | Δ A-B |
|---|---:|---:|---:|
| Faithfulness | 1.0000 | 1.0000 | +0.0000 |
| Answer Relevance | 0.3148 | 0.3094 | +0.0054 |
| Context Recall | 0.8557 | 0.8715 | -0.0158 |
| Context Precision | 0.6250 | 0.6000 | +0.0250 |
| Average | 0.6989 | 0.6952 | +0.0037 |

## A/B Comparison Analysis

- **Config A:** Dense + BM25, RRF fusion, local relevance rerank, structural fallback.
- **Config B:** Dense retrieval only, no reranking, no forced fallback.
- **Conclusion:** `A_hybrid_rerank` has the higher/equal macro average on this corpus. Context recall and precision should be read together: retrieving more evidence is useful only when irrelevant chunks stay controlled.

## Worst Performers (Bottom 3)

| # | Question | Faithfulness | Relevance | Recall | Precision | Failure stage |
|---:|---|---:|---:|---:|---:|---|
| 1 | Sàn có thể xử lý người bán vi phạm quy định đăng bán như thế nào? | 1.0000 | 0.0333 | 0.6957 | 0.4000 | answer_selection |
| 2 | Người mua có thể yêu cầu trả hàng/hoàn tiền trong thời hạn bao lâu sau khi nhận hàng? | 1.0000 | 0.0889 | 0.7222 | 0.4000 | answer_selection |
| 3 | Người bán không được đăng bán những sản phẩm nào? | 1.0000 | 0.0000 | 0.6522 | 0.6000 | answer_selection |

## Recommendations

1. **Calibrate fallback on a larger validation split.** Sweep the original dense cosine threshold and optimize recall without using the small RRF score.
2. **Improve sentence-level generation.** Merge adjacent evidence sentences and remove navigation/header text before generation to increase answer relevance.
3. **Add hard negatives and role filters.** Benchmark near-duplicate payment/refund questions and enforce `customer_role` for buyer-versus-seller precision.

## Reproduce

```powershell
python -m group_project.evaluation.eval_pipeline
```
