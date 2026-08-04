"""Reproducible RAG evaluation with a RAGAS path and an offline CI fallback.

Set ``RAGAS_USE_LLM=1`` to run the official RAGAS metrics. The default evaluator uses
deterministic token-support proxies for the same four dimensions so CI and live demos do
not consume API quota. It never presents those proxy scores as LLM-judged RAGAS scores.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from statistics import mean

PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.retrieval_utils import normalize_text, tokenize
from src.task10_generation import _extractive_answer, generate_with_citation
from src.task9_retrieval_pipeline import retrieve

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_PATH = Path(__file__).parent / "results.md"
METRICS = ("faithfulness", "answer_relevance", "context_recall", "context_precision")
STOPWORDS = {
    "a", "an", "the", "is", "are", "of", "to", "and", "or", "in", "for", "with",
    "la", "va", "cua", "co", "the", "duoc", "nhung", "mot", "khi", "cho", "voi",
    "nay", "do", "toi", "can", "khong", "sau", "neu", "tu", "trong", "de",
}


def load_golden_dataset() -> list[dict]:
    data = json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8-sig"))
    if len(data) < 15:
        raise ValueError(f"Golden dataset requires at least 15 cases, found {len(data)}")
    required = {"question", "expected_answer", "expected_context"}
    for index, item in enumerate(data):
        missing = required - item.keys()
        if missing:
            raise ValueError(f"Case {index} is missing: {sorted(missing)}")
    return data


def _terms(text: str) -> set[str]:
    return {token for token in tokenize(text) if len(token) > 1 and token not in STOPWORDS}


def _f1(left: str, right: str) -> float:
    a, b = _terms(left), _terms(right)
    if not a or not b:
        return 0.0
    overlap = len(a & b)
    precision, recall = overlap / len(a), overlap / len(b)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _run_case(question: str, config: dict | None = None, rag_pipeline=None) -> dict:
    config = config or {}
    if rag_pipeline is not None and not config:
        function = getattr(rag_pipeline, "generate_with_citation", rag_pipeline)
        return function(question)
    chunks = retrieve(
        question,
        top_k=config.get("top_k", 5),
        score_threshold=config.get("score_threshold", 0.16),
        use_reranking=config.get("use_reranking", True),
        retrieval_mode=config.get("retrieval_mode", "hybrid"),
    )
    return {"answer": _extractive_answer(question, chunks), "sources": chunks}


def _score_case(item: dict, result: dict) -> dict:
    answer = result.get("answer", "")
    # Citation labels are provenance, not answer claims; exclude them from lexical metrics.
    scored_answer = re.sub(r"\[[^\]]+\]", "", answer)
    sources = result.get("sources", [])
    contexts = [source.get("content", "") for source in sources]
    joined_context = " ".join(contexts)
    answer_terms, context_terms = _terms(scored_answer), _terms(joined_context)
    expected_terms = _terms(item["expected_answer"])

    faithfulness = len(answer_terms & context_terms) / len(answer_terms) if answer_terms else 0.0
    answer_relevance = _f1(scored_answer, item["expected_answer"])
    context_recall = len(expected_terms & context_terms) / len(expected_terms) if expected_terms else 0.0

    expected_source = item.get("expected_source")
    useful = 0
    for source in sources:
        source_name = (source.get("metadata") or {}).get("source")
        if source_name == expected_source or _f1(source.get("content", ""), item["expected_answer"]) >= 0.18:
            useful += 1
    context_precision = useful / len(sources) if sources else 0.0
    scores = {
        "faithfulness": faithfulness,
        "answer_relevance": answer_relevance,
        "context_recall": context_recall,
        "context_precision": context_precision,
    }
    failure_stage = "none"
    if context_recall < 0.5:
        failure_stage = "retrieval"
    elif faithfulness < 0.8:
        failure_stage = "generation"
    elif answer_relevance < 0.45:
        failure_stage = "answer_selection"
    return {
        "question": item["question"],
        "answer": answer,
        "expected_source": expected_source,
        **{name: round(value, 4) for name, value in scores.items()},
        "average": round(mean(scores.values()), 4),
        "failure_stage": failure_stage,
        "retrieved_sources": [(source.get("metadata") or {}).get("source", "unknown") for source in sources],
    }


def evaluate_offline(rag_pipeline, golden_dataset: list[dict], config: dict | None = None) -> dict:
    cases = [_score_case(item, _run_case(item["question"], config, rag_pipeline)) for item in golden_dataset]
    overall = {metric: round(mean(case[metric] for case in cases), 4) for metric in METRICS}
    overall["average"] = round(mean(overall.values()), 4)
    return {
        "framework": "RAGAS-compatible deterministic CI proxy (no LLM judge)",
        "overall": overall,
        "cases": cases,
        "case_count": len(cases),
    }


def evaluate_with_ragas(rag_pipeline, golden_dataset: list[dict]) -> dict:
    """Run official RAGAS when opted in, otherwise return transparent proxy metrics."""
    if os.getenv("RAGAS_USE_LLM", "0") != "1":
        return evaluate_offline(rag_pipeline, golden_dataset)

    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

    records = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    raw_results = []
    for item in golden_dataset:
        result = _run_case(item["question"], rag_pipeline=rag_pipeline)
        raw_results.append(result)
        records["question"].append(item["question"])
        records["answer"].append(result.get("answer", ""))
        records["contexts"].append([source.get("content", "") for source in result.get("sources", [])])
        records["ground_truth"].append(item["expected_answer"])
    evaluated = evaluate(
        Dataset.from_dict(records),
        metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
    ).to_pandas()
    cases = []
    for index, row in evaluated.iterrows():
        scores = {
            "faithfulness": float(row["faithfulness"]),
            "answer_relevance": float(row["answer_relevancy"]),
            "context_recall": float(row["context_recall"]),
            "context_precision": float(row["context_precision"]),
        }
        cases.append({"question": golden_dataset[index]["question"], **scores, "average": mean(scores.values())})
    overall = {metric: round(mean(case[metric] for case in cases), 4) for metric in METRICS}
    overall["average"] = round(mean(overall.values()), 4)
    return {"framework": "RAGAS (LLM judge)", "overall": overall, "cases": cases, "case_count": len(cases)}


def compare_configs(rag_pipeline, golden_dataset: list[dict]) -> dict:
    configs = {
        "A_hybrid_rerank": {
            "description": "Dense + BM25, RRF fusion, local relevance rerank, structural fallback",
            "params": {"retrieval_mode": "hybrid", "use_reranking": True, "top_k": 5},
        },
        "B_dense_only": {
            "description": "Dense retrieval only, no reranking, no forced fallback",
            "params": {"retrieval_mode": "dense", "use_reranking": False, "score_threshold": -1, "top_k": 5},
        },
    }
    output = {}
    for name, config in configs.items():
        evaluation = evaluate_offline(None, golden_dataset, config["params"])
        output[name] = {**config, **evaluation}
    a, b = output["A_hybrid_rerank"]["overall"], output["B_dense_only"]["overall"]
    output["delta_A_minus_B"] = {metric: round(a[metric] - b[metric], 4) for metric in (*METRICS, "average")}
    output["winner"] = "A_hybrid_rerank" if a["average"] >= b["average"] else "B_dense_only"
    return output


def export_results(results: dict, comparison: dict) -> Path:
    a = comparison["A_hybrid_rerank"]
    b = comparison["B_dense_only"]
    delta = comparison["delta_A_minus_B"]
    labels = {
        "faithfulness": "Faithfulness",
        "answer_relevance": "Answer Relevance",
        "context_recall": "Context Recall",
        "context_precision": "Context Precision",
        "average": "Average",
    }
    lines = [
        "# RAG Evaluation Results", "", f"**Generated from:** {results['case_count']} golden cases",
        f"**Evaluator:** {results['framework']}", "",
        "> The default report uses deterministic support metrics for reproducible offline CI. "
        "Set `RAGAS_USE_LLM=1` for the official RAGAS LLM judge; do not compare the two score types directly.",
        "", "## Overall Scores", "",
        "| Metric | Config A: hybrid + rerank | Config B: dense-only | Δ A-B |",
        "|---|---:|---:|---:|",
    ]
    for metric in (*METRICS, "average"):
        lines.append(f"| {labels[metric]} | {a['overall'][metric]:.4f} | {b['overall'][metric]:.4f} | {delta[metric]:+.4f} |")
    winner = comparison["winner"]
    lines += [
        "", "## A/B Comparison Analysis", "",
        f"- **Config A:** {a['description']}.",
        f"- **Config B:** {b['description']}.",
        f"- **Conclusion:** `{winner}` has the higher/equal macro average on this corpus. "
        "Context recall and precision should be read together: retrieving more evidence is useful only when irrelevant chunks stay controlled.",
        "", "## Worst Performers (Bottom 3)", "",
        "| # | Question | Faithfulness | Relevance | Recall | Precision | Failure stage |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    worst = sorted(a["cases"], key=lambda case: case["average"])[:3]
    for index, case in enumerate(worst, 1):
        question = case["question"].replace("|", "\\|")
        lines.append(
            f"| {index} | {question} | {case['faithfulness']:.4f} | {case['answer_relevance']:.4f} | "
            f"{case['context_recall']:.4f} | {case['context_precision']:.4f} | {case['failure_stage']} |"
        )
    lines += [
        "", "## Recommendations", "",
        "1. **Calibrate fallback on a larger validation split.** Sweep the original dense cosine threshold and optimize recall without using the small RRF score.",
        "2. **Improve sentence-level generation.** Merge adjacent evidence sentences and remove navigation/header text before generation to increase answer relevance.",
        "3. **Add hard negatives and role filters.** Benchmark near-duplicate payment/refund questions and enforce `customer_role` for buyer-versus-seller precision.",
        "", "## Reproduce", "", "```powershell", "python -m group_project.evaluation.eval_pipeline", "```", "",
    ]
    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")
    return RESULTS_PATH


def main() -> None:
    golden = load_golden_dataset()
    results = evaluate_with_ragas(generate_with_citation, golden)
    comparison = compare_configs(generate_with_citation, golden)
    path = export_results(results, comparison)
    print(json.dumps({"cases": len(golden), "winner": comparison["winner"], "report": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
