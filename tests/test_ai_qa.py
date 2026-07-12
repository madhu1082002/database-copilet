import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from qa.hallucination_checker import aggregate_hallucination_rate, check_hallucination
from qa.response_scorer import score_response_rule_based
from qa.run_ai_qa import load_test_queries, run_qa_suite
from qa.synthetic_query_generator import generate_template_queries
from services import data_service
from services.gemini_service import _mock_response
from services.intent_classifier import classify_intent
from services.prompt_builder import build_context_for_intent


TEST_QUERIES_FILE = ROOT / "data" / "test_queries.json"


@pytest.fixture(scope="module")
def test_queries():
    if not TEST_QUERIES_FILE.exists():
        pytest.skip("test_queries.json missing — run scripts/build_test_queries.py")
    return load_test_queries(TEST_QUERIES_FILE)


def test_synthetic_generator_produces_queries():
    queries = generate_template_queries(count=55)
    assert len(queries) >= 50
    assert all("query" in q and "expected_intent" in q for q in queries)


def test_intent_accuracy_on_test_queries(test_queries):
    correct = 0
    evaluated = 0
    for item in test_queries:
        if not item["query"].strip():
            continue
        evaluated += 1
        actual = classify_intent(item["query"])
        if actual == item["expected_intent"]:
            correct += 1
    accuracy = correct / evaluated if evaluated else 0
    assert accuracy >= 0.85, f"Intent accuracy {accuracy:.2%} below 85% target"


def test_mock_responses_low_hallucination(test_queries):
    known_pipelines = {p["pipeline_name"] for p in data_service.get_all_pipelines()}
    hallucination_results = []

    for item in test_queries:
        if not item["query"].strip():
            continue
        intent = classify_intent(item["query"])
        pipeline = data_service.extract_pipeline_name_from_query(item["query"]) or item.get("pipeline")
        context = build_context_for_intent(intent, pipeline, data_service)
        response = _mock_response(intent, context)
        result = check_hallucination(response, context, known_pipelines)
        hallucination_results.append(result)

    rate = aggregate_hallucination_rate(hallucination_results)
    assert rate <= 0.10, f"Hallucination rate {rate:.2%} exceeds 10% target"


def test_response_scorer_returns_scores(test_queries):
    item = next(q for q in test_queries if q["expected_intent"] == "failure_diagnosis" and q.get("pipeline"))
    intent = classify_intent(item["query"])
    context = build_context_for_intent(intent, item["pipeline"], data_service)
    response = _mock_response(intent, context)
    scores = score_response_rule_based(
        item["query"], response, item["expected_intent"], intent, context
    )
    assert scores["overall_score"] >= 50
    assert "hallucination" in scores


def test_run_ai_qa_suite(test_queries):
    report = run_qa_suite(test_queries[:20], use_gemini_scoring=False, use_gemini_responses=False)
    assert report["evaluated"] > 0
    assert report["intent_accuracy"] >= 0.0
    assert report["hallucination_rate"] <= 0.10
    assert report["average_overall_score"] >= 50
