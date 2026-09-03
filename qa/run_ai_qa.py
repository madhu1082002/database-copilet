#!/usr/bin/env python3
"""Run AI-assisted QA: synthetic queries, response scoring, hallucination measurement."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

os.environ.setdefault("USE_DATABRICKS", "false")
if "--use-gemini-responses" in sys.argv:
    os.environ["USE_MOCK_AI"] = "false"
else:
    os.environ.setdefault("USE_MOCK_AI", "true")

from qa.hallucination_checker import aggregate_hallucination_rate  # noqa: E402
from qa.response_scorer import score_response_rule_based, score_response_with_gemini  # noqa: E402
from qa.synthetic_query_generator import generate_gemini_queries, generate_template_queries  # noqa: E402
from services import data_service  # noqa: E402
from services.gemini_service import generate_response  # noqa: E402
from services.intent_classifier import classify_intent  # noqa: E402
from services.prompt_builder import build_context_for_intent, build_prompt  # noqa: E402

DEFAULT_QUERIES_FILE = ROOT / "data" / "test_queries.json"
REPORTS_DIR = ROOT / "reports"


def load_test_queries(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("queries", payload)


def run_qa_suite(
    queries: list[dict],
    use_gemini_scoring: bool = False,
    use_gemini_responses: bool = False,
) -> dict:
    known_pipelines = {p["pipeline_name"] for p in data_service.get_all_pipelines()}
    results = []

    for item in queries:
        query = item["query"]
        expected_intent = item.get("expected_intent", "pipeline_status")

        if not query.strip():
            results.append(
                {
                    "id": item.get("id"),
                    "query": query,
                    "skipped": True,
                    "reason": "empty query",
                }
            )
            continue

        actual_intent = classify_intent(query, item.get("category_hint"))
        pipeline_name = data_service.extract_pipeline_name_from_query(query) or item.get("pipeline")
        context = build_context_for_intent(actual_intent, pipeline_name, data_service)
        prompt = build_prompt(query, actual_intent, context)

        if use_gemini_responses:
            response = generate_response(prompt, actual_intent, context)
        else:
            from services.gemini_service import _mock_response

            response = _mock_response(actual_intent, context)

        scorer = score_response_with_gemini if use_gemini_scoring else score_response_rule_based
        scores = scorer(query, response, expected_intent, actual_intent, context, known_pipelines)

        results.append(
            {
                "id": item.get("id"),
                "query": query,
                "category": item.get("category"),
                "response_preview": response[:240],
                "scores": scores,
            }
        )

    evaluated = [r for r in results if not r.get("skipped")]
    intent_accuracy = (
        sum(1 for r in evaluated if r["scores"]["intent_match"]) / len(evaluated) if evaluated else 0.0
    )
    hallucination_results = [r["scores"]["hallucination"] for r in evaluated]
    avg_overall = (
        sum(r["scores"]["overall_score"] for r in evaluated) / len(evaluated) if evaluated else 0.0
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_queries": len(queries),
        "evaluated": len(evaluated),
        "skipped": len(results) - len(evaluated),
        "intent_accuracy": round(intent_accuracy, 4),
        "hallucination_rate": aggregate_hallucination_rate(hallucination_results),
        "average_overall_score": round(avg_overall, 2),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AI-assisted QA for DataOps Copilot")
    parser.add_argument("--queries-file", type=Path, default=DEFAULT_QUERIES_FILE)
    parser.add_argument("--synthetic", type=int, default=0, help="Add N template-generated queries")
    parser.add_argument("--gemini-synthetic", type=int, default=0, help="Add N Gemini-generated queries")
    parser.add_argument("--use-gemini-scoring", action="store_true")
    parser.add_argument("--use-gemini-responses", action="store_true")
    parser.add_argument("--output", type=Path, default=REPORTS_DIR / "ai_qa_report.json")
    parser.add_argument("--limit", type=int, default=0, help="Evaluate only the first N queries (0 = all)")
    args = parser.parse_args()

    queries = load_test_queries(args.queries_file) if args.queries_file.exists() else []

    if args.synthetic:
        queries.extend(generate_template_queries(count=args.synthetic))

    if args.gemini_synthetic:
        queries.extend(generate_gemini_queries(count=args.gemini_synthetic))

    if not queries:
        print("No queries to evaluate. Run scripts/build_test_queries.py first.", file=sys.stderr)
        return 1

    if args.limit and args.limit > 0:
        queries = queries[: args.limit]

    report = run_qa_suite(
        queries,
        use_gemini_scoring=args.use_gemini_scoring,
        use_gemini_responses=args.use_gemini_responses,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps(
        {
            "evaluated": report["evaluated"],
            "intent_accuracy": report["intent_accuracy"],
            "hallucination_rate": report["hallucination_rate"],
            "average_overall_score": report["average_overall_score"],
            "report": str(args.output),
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
