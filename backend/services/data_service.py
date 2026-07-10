import json
from pathlib import Path

from config import DATA_DIR
from services import databricks_service


def _load_json(filename: str) -> list:
    path = DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _using_databricks() -> bool:
    return databricks_service.is_configured()


def _filter_by_name(items: list[dict], name_field: str, pipeline_name: str | None) -> list[dict]:
    if not pipeline_name:
        return items
    name_lower = pipeline_name.lower().replace(" ", "_")
    return [
        item for item in items
        if name_lower in item[name_field].lower()
        or item[name_field].lower().replace("_", " ") in pipeline_name.lower()
    ]


def get_data_source() -> str:
    if not _using_databricks():
        return "mock_json"
    if databricks_service.has_sql_warehouse():
        pipelines = databricks_service.get_pipelines_from_table()
        if pipelines:
            return "databricks_tables"
    return "databricks"


def get_all_pipelines() -> list[dict]:
    if _using_databricks():
        runs = databricks_service.get_job_runs()
        if runs:
            return runs
    return _load_json("pipelines.json")


def get_pipeline_status(pipeline_name: str | None = None) -> list[dict]:
    return _filter_by_name(get_all_pipelines(), "pipeline_name", pipeline_name)


def get_failed_pipelines(hours: int = 24) -> list[dict]:
    if _using_databricks():
        failed = databricks_service.get_failed_runs()
        if failed:
            return failed
    return [p for p in get_all_pipelines() if p["status"] in ("failed", "partial_failure")]


def get_failure_diagnosis(pipeline_name: str | None = None) -> list[dict]:
    if _using_databricks():
        failures = databricks_service.get_failure_records(pipeline_name)
        if failures:
            return failures
    failures = _load_json("failures.json")
    return _filter_by_name(failures, "pipeline_name", pipeline_name)


def get_optimization_data() -> list[dict]:
    if _using_databricks():
        clusters = databricks_service.get_clusters()
        if clusters:
            return clusters
    return _load_json("clusters.json")


def get_dashboard_summary() -> dict:
    pipelines = get_all_pipelines()
    total = len(pipelines)
    success = sum(1 for p in pipelines if p["status"] == "success")
    failed = sum(1 for p in pipelines if p["status"] in ("failed", "partial_failure", "unknown"))
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
        "data_source": get_data_source(),
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
