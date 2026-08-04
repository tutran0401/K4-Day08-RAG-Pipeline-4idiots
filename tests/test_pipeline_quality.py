"""Small regression suite for behavior not covered by the grading smoke tests."""

from group_project.evaluation.eval_pipeline import load_golden_dataset
from src.task10_generation import expand_follow_up_query, generate_with_citation
from src.task7_reranking import rerank_rrf
from src.task6_lexical_search import build_tfidf_index


def test_golden_dataset_meets_group_requirement():
    assert len(load_golden_dataset()) >= 15


def test_unknown_question_does_not_hallucinate():
    result = generate_with_citation("xyzabc123nonsense")
    assert "không thể xác minh" in result["answer"].lower()


def test_known_answer_contains_citation():
    question = load_golden_dataset()[1]["question"]
    result = generate_with_citation(question)
    assert "[" in result["answer"] and "]" in result["answer"]
    assert result["sources"]


def test_follow_up_query_uses_recent_user_context():
    history = [{"role": "user", "content": "Các phương thức thanh toán được hỗ trợ là gì?"}]
    expanded = expand_follow_up_query("Còn COD thì sao?", history)
    assert "phương thức thanh toán" in expanded
    assert "COD" in expanded


def test_rrf_rewards_documents_found_by_both_rankers():
    shared = {"id": "shared", "content": "shared", "score": 0.8, "metadata": {}}
    dense = [shared, {"id": "dense", "content": "dense", "score": 0.7, "metadata": {}}]
    sparse = [{"id": "sparse", "content": "sparse", "score": 4.0, "metadata": {}}, shared]
    assert rerank_rrf([dense, sparse], top_k=1)[0]["id"] == "shared"


def test_tfidf_bonus_backend_ranks_exact_term_match():
    corpus = [
        {"content": "payment wallet card", "metadata": {}},
        {"content": "seller prohibited listing", "metadata": {}},
    ]
    scores = build_tfidf_index(corpus).get_scores(["payment", "wallet"])
    assert scores[0] > scores[1]
