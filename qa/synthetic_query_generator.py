"""Generate synthetic test queries from mock pipeline data (Gemini or templates)."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "backend" / "data"

STATUS_TEMPLATES = [
    "Did {pipeline} run today?",
    "What is the status of {display}?",
    "Show me the latest run for {pipeline}",
    "Has {display} completed successfully?",
    "When did {pipeline} last run?",
    "Is {display} still running?",
]

FAILURE_TEMPLATES = [
    "Why did {pipeline} fail?",
    "What caused the {display} failure?",
    "Show error details for {pipeline}",
    "What went wrong with {display}?",
    "Diagnose the failure on {pipeline}",
    "Root cause for {display} failure?",
]

OPTIMIZATION_TEMPLATES = [
    "Can we reduce compute costs?",
    "Which clusters are oversized?",
    "How can runtime performance be improved?",
    "Which jobs consume high resources?",
    "Show optimization opportunities for {cluster}",
    "Is {cluster} underutilized?",
]

EDGE_TEMPLATES = [
    "What is the weather today?",
    "",
    "Tell me about pipeline xyz_nonexistent_999",
    "Why did everything fail and also optimize all clusters?",
    "STATUS??? {pipeline} !!!",
    "Did sales_etl run and why did customer_ingestion fail?",
]


def load_mock_pipelines() -> list[dict]:
    with open(DATA_DIR / "pipelines.json", encoding="utf-8") as f:
        return json.load(f)


def load_mock_clusters() -> list[dict]:
    with open(DATA_DIR / "clusters.json", encoding="utf-8") as f:
        return json.load(f)


def generate_template_queries(count: int = 30, seed: int = 42) -> list[dict]:
    """Build diverse queries from mock data without calling Gemini."""
    random.seed(seed)
    pipelines = load_mock_pipelines()
    clusters = load_mock_clusters()

    failed = [p for p in pipelines if p["status"] in ("failed", "partial_failure")]
    success = [p for p in pipelines if p["status"] == "success"]
    running = [p for p in pipelines if p["status"] == "running"]
    undersized = [c for c in clusters if c.get("estimated_savings_inr", 0) > 0]

    queries: list[dict] = []
    idx = 1

    def add(query: str, intent: str, category: str, pipeline: str | None = None):
        nonlocal idx
        if not query.strip():
            category = "malformed"
            intent = "pipeline_status"
        queries.append(
            {
                "id": f"syn-{idx:03d}",
                "query": query,
                "expected_intent": intent,
                "category": category,
                "pipeline": pipeline,
                "source": "template",
            }
        )
        idx += 1

    for p in success[:12]:
        tpl = random.choice(STATUS_TEMPLATES)
        add(
            tpl.format(pipeline=p["pipeline_name"], display=p["pipeline_name"].replace("_", " ")),
            "pipeline_status",
            "standard",
            p["pipeline_name"],
        )

    for p in running[:4]:
        add(
            f"Is {p['pipeline_name'].replace('_', ' ')} still running?",
            "pipeline_status",
            "standard",
            p["pipeline_name"],
        )

    add("Which pipelines failed in the last 24 hours?", "pipeline_status", "aggregate")
    add("Show me all failed pipelines", "pipeline_status", "aggregate")
    add("How many pipelines succeeded today?", "pipeline_status", "aggregate")

    for p in failed:
        tpl = random.choice(FAILURE_TEMPLATES)
        add(
            tpl.format(pipeline=p["pipeline_name"], display=p["pipeline_name"].replace("_", " ")),
            "failure_diagnosis",
            "standard",
            p["pipeline_name"],
        )

    for tpl in OPTIMIZATION_TEMPLATES[:4]:
        add(tpl.format(cluster="analytics_cluster"), "optimization", "standard")

    for c in undersized[:8]:
        add(
            f"Can we save money on {c['cluster_name']}?",
            "optimization",
            "standard",
            None,
        )

    for tpl in EDGE_TEMPLATES:
        pipeline = random.choice(pipelines)["pipeline_name"] if "{pipeline}" in tpl else None
        q = tpl.format(pipeline=pipeline or "sales_etl") if "{pipeline}" in tpl else tpl
        intent = "failure_diagnosis" if "fail" in q.lower() and "optimize" in q.lower() else (
            "failure_diagnosis" if "fail" in q.lower() else "pipeline_status"
        )
        add(q, intent, "edge_case", pipeline)

    while len(queries) < count:
        p = random.choice(pipelines)
        add(
            random.choice(STATUS_TEMPLATES).format(
                pipeline=p["pipeline_name"],
                display=p["pipeline_name"].replace("_", " "),
            ),
            "pipeline_status",
            "synthetic_extra",
            p["pipeline_name"],
        )

    return queries[:count]


def generate_gemini_queries(count: int = 20) -> list[dict]:
    """Use Gemini to propose additional edge-case queries grounded in mock data."""
    try:
        from config import GEMINI_API_KEYS, USE_MOCK_AI
        from services.gemini_service import _call_gemini
    except ImportError:
        return []

    if USE_MOCK_AI or not GEMINI_API_KEYS:
        return []

    pipelines = load_mock_pipelines()
    sample_names = [p["pipeline_name"] for p in pipelines[:15]]

    prompt = f"""Generate {count} diverse natural-language test queries for a DataOps AI assistant.
Use ONLY these real pipeline names: {', '.join(sample_names)}

Include:
- pipeline status questions
- failure diagnosis questions
- optimization / cost questions
- ambiguous or multi-part questions
- one out-of-scope question

Return ONLY a JSON array:
[{{"query":"...", "expected_intent":"pipeline_status|failure_diagnosis|optimization", "category":"gemini_synthetic"}}]
"""

    try:
        raw = _call_gemini(GEMINI_API_KEYS[0], prompt)
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1:
            return []
        items = json.loads(raw[start : end + 1])
        results = []
        for i, item in enumerate(items, start=1):
            results.append(
                {
                    "id": f"gem-{i:03d}",
                    "query": item["query"],
                    "expected_intent": item.get("expected_intent", "pipeline_status"),
                    "category": item.get("category", "gemini_synthetic"),
                    "pipeline": None,
                    "source": "gemini",
                }
            )
        return results
    except Exception as exc:
        logger.warning("Gemini synthetic query generation failed: %s", exc)
        return []
