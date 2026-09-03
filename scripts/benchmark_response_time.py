#!/usr/bin/env python3
"""Measure /query response times through the Flask test client (no live network)."""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

os.environ["USE_DATABRICKS"] = "false"
os.environ["USE_MOCK_AI"] = "true"

from app import app  # noqa: E402
from services.response_cache import cache_clear  # noqa: E402

QUERIES = [
    "Did sales_etl run today?",
    "Why did customer_ingestion fail?",
    "Can we reduce compute costs?",
    "Which pipelines failed in the last 24 hours?",
    "Show me the status of Customer Sync",
]


def main() -> int:
    cache_clear()
    times: list[float] = []
    app.config["TESTING"] = True
    with app.test_client() as client:
        for i in range(50):
            query = QUERIES[i % len(QUERIES)]
            start = time.perf_counter()
            res = client.post("/query", json={"query": query})
            elapsed = time.perf_counter() - start
            if res.status_code != 200:
                print(f"FAIL status={res.status_code} query={query}", file=sys.stderr)
                return 1
            times.append(elapsed)

    times_sorted = sorted(times)
    p50 = times_sorted[len(times_sorted) // 2]
    p95 = times_sorted[int(len(times_sorted) * 0.95) - 1]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "flask_test_client_mock_ai",
        "queries": 50,
        "min_s": round(min(times), 4),
        "max_s": round(max(times), 4),
        "mean_s": round(statistics.mean(times), 4),
        "p50_s": round(p50, 4),
        "p95_s": round(p95, 4),
        "under_10s": all(t < 10 for t in times),
    }

    out_json = ROOT / "reports" / "load_test_report.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md = ROOT / "docs" / "LOAD_TEST.md"
    md.write_text(
        "# Load / response-time evidence\n\n"
        f"Generated: {report['generated_at']}\n\n"
        "50 mixed queries (status, failure, optimization) via Flask test client, "
        "mock AI path, cache enabled after first cycle.\n\n"
        f"| Metric | Value |\n|--------|-------|\n"
        f"| Queries | {report['queries']} |\n"
        f"| Min | {report['min_s']} s |\n"
        f"| Mean | {report['mean_s']} s |\n"
        f"| p50 | {report['p50_s']} s |\n"
        f"| p95 | {report['p95_s']} s |\n"
        f"| Max | {report['max_s']} s |\n"
        f"| All under 10s | {'Yes' if report['under_10s'] else 'No'} |\n\n"
        "Locust (optional live HTTP): `pip install -r requirements-dev.txt` then "
        "`locust -f locustfile.py --headless -u 10 -r 2 -t 60s --host http://127.0.0.1:5000`.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
