import json
from pathlib import Path

from config import DATA_DIR


def _load_json(filename: str) -> list:
    path = DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_all_pipelines() -> list[dict]:
    return _load_json("pipelines.json")


def get_pipeline_status(pipeline_name: str | None = None) -> list[dict]:
    pipelines = get_all_pipelines()
    if pipeline_name:
        name_lower = pipeline_name.lower().replace(" ", "_")
        pipelines = [
            p for p in pipelines
            if name_lower in p["pipeline_name"].lower()
            or p["pipeline_name"].lower().replace("_", " ") in pipeline_name.lower()
        ]
    return pipelines


def get_failed_pipelines(hours: int = 24) -> list[dict]:
    return [p for p in get_all_pipelines() if p["status"] in ("failed", "partial_failure")]


def get_failure_diagnosis(pipeline_name: str | None = None) -> list[dict]:
    failures = _load_json("failures.json")
    if pipeline_name:
        name_lower = pipeline_name.lower().replace(" ", "_")
        failures = [
            f for f in failures
            if name_lower in f["pipeline_name"].lower()
            or f["pipeline_name"].lower().replace("_", " ") in pipeline_name.lower()
        ]
    return failures


def get_optimization_data() -> list[dict]:
    return _load_json("clusters.json")


def get_dashboard_summary() -> dict:
    pipelines = get_all_pipelines()
    total = len(pipelines)
    success = sum(1 for p in pipelines if p["status"] == "success")
    failed = sum(1 for p in pipelines if p["status"] in ("failed", "partial_failure"))
    running = sum(1 for p in pipelines if p["status"] == "running")
    clusters = get_optimization_data()
    savings = sum(c.get("estimated_savings_inr", 0) for c in clusters)

    return {
        "total_pipelines": total,
        "success_count": success,
        "failed_count": failed,
        "running_count": running,
        "potential_monthly_savings_inr": savings,
        "pipelines": pipelines,
    }


def extract_pipeline_name_from_query(query: str) -> str | None:
    pipelines = get_all_pipelines()
    query_lower = query.lower()
    for p in pipelines:
        name = p["pipeline_name"]
        display = name.replace("_", " ")
        if name.lower() in query_lower or display.lower() in query_lower:
            return name
    return None
