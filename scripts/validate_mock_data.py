#!/usr/bin/env python3
"""Validate mock JSON datasets meet pSIDDHI 50+ scenario requirements."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "backend" / "data"

REQUIRED_PIPELINE_FIELDS = {
    "pipeline_name",
    "status",
    "run_time",
    "duration_minutes",
    "error_message",
    "cluster_id",
    "cpu_usage",
    "memory_usage",
    "dependencies",
    "last_success",
}

REQUIRED_FAILURE_FIELDS = {
    "pipeline_name",
    "failure_time",
    "root_cause",
    "error_details",
    "cluster_logs",
    "dependency_status",
    "suggested_actions",
}

REQUIRED_CLUSTER_FIELDS = {
    "cluster_id",
    "cluster_name",
    "instance_type",
    "recommended_type",
    "avg_cpu_usage",
    "avg_memory_usage",
    "monthly_cost_inr",
    "estimated_savings_inr",
    "recommendation",
}


def _load(name: str) -> list:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _check_schema(items: list, required: set[str], label: str) -> list[str]:
    errors = []
    for i, item in enumerate(items):
        missing = required - set(item.keys())
        if missing:
            errors.append(f"{label}[{i}] missing fields: {sorted(missing)}")
    return errors


def validate() -> tuple[bool, dict]:
    pipelines = _load("pipelines.json")
    failures = _load("failures.json")
    clusters = _load("clusters.json")

    errors: list[str] = []
    errors.extend(_check_schema(pipelines, REQUIRED_PIPELINE_FIELDS, "pipelines"))
    errors.extend(_check_schema(failures, REQUIRED_FAILURE_FIELDS, "failures"))
    errors.extend(_check_schema(clusters, REQUIRED_CLUSTER_FIELDS, "clusters"))

    statuses = {p["status"] for p in pipelines}
    required_statuses = {"success", "failed", "partial_failure", "running"}
    missing_statuses = required_statuses - statuses
    if missing_statuses:
        errors.append(f"Missing pipeline status scenarios: {sorted(missing_statuses)}")

    failed_pipelines = {p["pipeline_name"] for p in pipelines if p["status"] in ("failed", "partial_failure")}
    failure_records = {f["pipeline_name"] for f in failures}
    uncovered = failed_pipelines - failure_records
    if uncovered:
        errors.append(f"Failed pipelines without failure_logs entry: {sorted(uncovered)}")

    summary = {
        "pipeline_count": len(pipelines),
        "failure_count": len(failures),
        "cluster_count": len(clusters),
        "status_breakdown": {s: sum(1 for p in pipelines if p["status"] == s) for s in sorted(statuses)},
        "optimization_opportunities": sum(1 for c in clusters if c.get("estimated_savings_inr", 0) > 0),
        "meets_50_plus_scenarios": len(pipelines) >= 50,
        "errors": errors,
    }
    return len(errors) == 0 and summary["meets_50_plus_scenarios"], summary


def main() -> int:
    ok, summary = validate()
    print(json.dumps(summary, indent=2))
    if not ok:
        print("\nValidation FAILED", file=sys.stderr)
        return 1
    print("\nValidation PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
