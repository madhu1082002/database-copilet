#!/usr/bin/env python3
"""Build data/test_queries.json with 50+ validation scenarios from mock data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from qa.synthetic_query_generator import generate_template_queries  # noqa: E402

OUTPUT = ROOT / "data" / "test_queries.json"
MIN_QUERIES = 50


def main() -> int:
    queries = generate_template_queries(count=max(MIN_QUERIES, 55))

    payload = {
        "version": 1,
        "description": "Validation queries for DataOps Copilot AI-assisted QA (pSIDDHI S3-D-08)",
        "total_queries": len(queries),
        "queries": queries,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(queries)} test queries to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
