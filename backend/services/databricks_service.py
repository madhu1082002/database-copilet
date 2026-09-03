import json
import logging
import time
from datetime import datetime, timezone

import requests

from config import (
    DATABRICKS_CATALOG,
    DATABRICKS_HOST,
    DATABRICKS_SCHEMA,
    DATABRICKS_TOKEN,
    DATABRICKS_WAREHOUSE_ID,
    USE_DATABRICKS,
)

logger = logging.getLogger(__name__)

RESULT_FAILED = {"FAILED", "TIMEDOUT", "CANCELED", "SKIPPED", "MAXIMUM_CONCURRENT_RUNS_REACHED"}


def is_configured() -> bool:
    return USE_DATABRICKS and bool(DATABRICKS_HOST and DATABRICKS_TOKEN)


def has_sql_warehouse() -> bool:
    return is_configured() and bool(DATABRICKS_WAREHOUSE_ID)


def _table(name: str) -> str:
    return f"{DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}.{name}"


def _headers() -> dict:
    return {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}


def _get(path: str, params: dict | None = None) -> dict:
    url = f"{DATABRICKS_HOST.rstrip('/')}{path}"
    response = requests.get(url, headers=_headers(), params=params or {}, timeout=30)
    response.raise_for_status()
    return response.json()


def _rows_to_dicts(result: dict) -> list[dict]:
    columns = [c["name"] for c in result.get("manifest", {}).get("schema", {}).get("columns", [])]
    rows = result.get("result", {}).get("data_array", [])
    return [dict(zip(columns, row)) for row in rows]


def execute_sql(statement: str) -> list[dict]:
    if not has_sql_warehouse():
        return []

    url = f"{DATABRICKS_HOST.rstrip('/')}/api/2.0/sql/statements"
    payload = {
        "warehouse_id": DATABRICKS_WAREHOUSE_ID,
        "statement": statement,
        "wait_timeout": "50s",
    }
    response = requests.post(url, headers=_headers(), json=payload, timeout=60)
    response.raise_for_status()
    statement_id = response.json().get("statement_id")

    for _ in range(30):
        status_resp = requests.get(f"{url}/{statement_id}", headers=_headers(), timeout=30)
        status_resp.raise_for_status()
        status_data = status_resp.json()
        state = status_data.get("status", {}).get("state")
        if state == "SUCCEEDED":
            return _rows_to_dicts(status_data)
        if state in {"FAILED", "CANCELED", "CLOSED"}:
            error = status_data.get("status", {}).get("error", {})
            raise RuntimeError(error.get("message", status_data))
        time.sleep(2)

    raise TimeoutError("Databricks SQL statement timed out")


def _parse_json_field(value, default):
    if value is None or value == "":
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _format_timestamp(value) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return value.replace(" ", "T") + ("Z" if "Z" not in value and "+" not in value else "")
    return str(value)


def _to_int(value, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _map_table_pipeline(row: dict) -> dict:
    return {
        "pipeline_name": row.get("pipeline_name"),
        "status": row.get("status"),
        "run_time": _format_timestamp(row.get("run_time")),
        "duration_minutes": _to_float(row.get("duration_minutes")),
        "error_message": row.get("error_message"),
        "cluster_id": row.get("cluster_id"),
        "cpu_usage": _to_float(row.get("cpu_usage")),
        "memory_usage": _to_float(row.get("memory_usage")),
        "dependencies": _parse_json_field(row.get("dependencies"), []),
        "last_success": _format_timestamp(row.get("last_success")),
        "source": "databricks_table",
    }


def _map_table_failure(row: dict) -> dict:
    return {
        "pipeline_name": row.get("pipeline_name"),
        "failure_time": _format_timestamp(row.get("failure_time")),
        "root_cause": row.get("root_cause"),
        "error_details": row.get("error_details"),
        "cluster_logs": row.get("cluster_logs"),
        "dependency_status": _parse_json_field(row.get("dependency_status"), {}),
        "suggested_actions": _parse_json_field(row.get("suggested_actions"), []),
        "source": "databricks_table",
    }


def _map_table_cluster(row: dict) -> dict:
    return {
        "cluster_id": row.get("cluster_id"),
        "cluster_name": row.get("cluster_name"),
        "instance_type": row.get("instance_type"),
        "recommended_type": row.get("recommended_type"),
        "avg_cpu_usage": _to_float(row.get("avg_cpu_usage")),
        "avg_memory_usage": _to_float(row.get("avg_memory_usage")),
        "peak_cpu_usage": _to_float(row.get("peak_cpu_usage")),
        "peak_memory_usage": _to_float(row.get("peak_memory_usage")),
        "monthly_cost_inr": _to_int(row.get("monthly_cost_inr")),
        "estimated_savings_inr": _to_int(row.get("estimated_savings_inr")),
        "jobs_running": _parse_json_field(row.get("jobs_running"), []),
        "recommendation": row.get("recommendation"),
        "source": "databricks_table",
    }


def get_pipelines_from_table(pipeline_name: str | None = None) -> list[dict]:
    if not has_sql_warehouse():
        return []

    try:
        sql = f"SELECT * FROM {_table('pipeline_runs')}"
        if pipeline_name:
            safe_name = pipeline_name.replace("'", "''")
            sql += f" WHERE LOWER(pipeline_name) LIKE '%{safe_name.lower()}%'"
        rows = execute_sql(sql)
        return [_map_table_pipeline(row) for row in rows]
    except Exception as e:
        logger.warning("Databricks pipeline_runs table query failed: %s", e)
        return []


def get_failures_from_table(pipeline_name: str | None = None) -> list[dict]:
    if not has_sql_warehouse():
        return []

    try:
        sql = f"SELECT * FROM {_table('failure_logs')}"
        if pipeline_name:
            safe_name = pipeline_name.replace("'", "''")
            sql += f" WHERE LOWER(pipeline_name) LIKE '%{safe_name.lower()}%'"
        rows = execute_sql(sql)
        return [_map_table_failure(row) for row in rows]
    except Exception as e:
        logger.warning("Databricks failure_logs table query failed: %s", e)
        return []


def get_clusters_from_table() -> list[dict]:
    if not has_sql_warehouse():
        return []

    try:
        rows = execute_sql(f"SELECT * FROM {_table('cluster_metrics')}")
        return [_map_table_cluster(row) for row in rows]
    except Exception as e:
        logger.warning("Databricks cluster_metrics table query failed: %s", e)
        return []


def _ms_to_iso(ms: int | None) -> str | None:
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _map_run_status(run: dict) -> str:
    lifecycle = run.get("state", {}).get("life_cycle_state", "")
    result = run.get("state", {}).get("result_state", "")

    if lifecycle in {"PENDING", "RUNNING", "TERMINATING"}:
        return "running"
    if result == "SUCCESS":
        return "success"
    if result in RESULT_FAILED:
        return "failed"
    return "unknown"


def _run_name(run: dict) -> str:
    if run.get("run_name"):
        return run["run_name"].lower().replace(" ", "_")
    job_id = run.get("job_id")
    return f"job_{job_id}" if job_id else f"run_{run.get('run_id', 'unknown')}"


def _map_run_to_pipeline(run: dict) -> dict:
    start_ms = run.get("start_time")
    end_ms = run.get("end_time")
    duration = None
    if start_ms and end_ms:
        duration = round((end_ms - start_ms) / 60000, 1)

    cluster_id = run.get("cluster_instance", {}).get("cluster_id") or run.get("cluster_id")

    return {
        "pipeline_name": _run_name(run),
        "status": _map_run_status(run),
        "run_time": _ms_to_iso(start_ms),
        "duration_minutes": duration,
        "error_message": run.get("state", {}).get("state_message"),
        "cluster_id": cluster_id,
        "cpu_usage": None,
        "memory_usage": None,
        "dependencies": [],
        "last_success": _ms_to_iso(end_ms) if _map_run_status(run) == "success" else None,
        "source": "databricks_jobs_api",
        "run_id": run.get("run_id"),
        "job_id": run.get("job_id"),
    }


def _map_run_to_failure(run: dict) -> dict:
    name = _run_name(run)
    return {
        "pipeline_name": name,
        "failure_time": _ms_to_iso(run.get("end_time") or run.get("start_time")),
        "root_cause": run.get("state", {}).get("result_state", "UNKNOWN"),
        "error_details": run.get("state", {}).get("state_message") or "No error details available",
        "cluster_logs": f"Run ID: {run.get('run_id')} | Job ID: {run.get('job_id')}",
        "dependency_status": {},
        "suggested_actions": [
            "Open the job run in Databricks UI for full logs",
            "Check cluster health and upstream dependencies",
            "Retry the failed job run after fixing the root cause",
        ],
        "source": "databricks_jobs_api",
    }


def _map_cluster_to_optimization(cluster: dict) -> dict:
    """Map Clusters API records without inventing CPU, memory, or ₹ savings."""
    node_type = cluster.get("node_type_id", "unknown")
    name = cluster.get("cluster_name") or cluster.get("cluster_id")
    state = cluster.get("state") or "UNKNOWN"

    return {
        "cluster_id": cluster.get("cluster_id"),
        "cluster_name": name,
        "instance_type": node_type,
        "recommended_type": None,
        "avg_cpu_usage": None,
        "avg_memory_usage": None,
        "peak_cpu_usage": None,
        "peak_memory_usage": None,
        "monthly_cost_inr": None,
        "estimated_savings_inr": 0,
        "jobs_running": [],
        "metrics_available": False,
        "recommendation": (
            f"Cluster '{name}' is {state} on {node_type}. "
            "CPU/memory utilization is not returned by the Databricks Clusters API, "
            "so quantified ₹ savings are not estimated here. "
            "Use the cluster_metrics Delta table (Pipeline Data Portal) for grounded optimization figures."
        ),
        "source": "databricks_clusters_api",
        "state": state,
    }


def get_job_runs(limit: int = 25) -> list[dict]:
    pipelines = get_pipelines_from_table()
    if pipelines:
        return pipelines

    if not is_configured():
        return []

    try:
        data = _get("/api/2.1/jobs/runs/list", {"limit": limit, "expand_tasks": "false"})
        runs = data.get("runs", [])
        return [_map_run_to_pipeline(run) for run in runs]
    except Exception as e:
        logger.warning("Databricks job runs fetch failed: %s", e)
        return []


def get_failed_runs(limit: int = 25) -> list[dict]:
    pipelines = get_job_runs(limit=limit)
    return [p for p in pipelines if p["status"] in ("failed", "unknown", "partial_failure")]


def get_failure_records(pipeline_name: str | None = None, limit: int = 25) -> list[dict]:
    failures = get_failures_from_table(pipeline_name)
    if failures:
        return failures

    if not is_configured():
        return []

    try:
        data = _get("/api/2.1/jobs/runs/list", {"limit": limit, "expand_tasks": "false"})
        failures = []
        for run in data.get("runs", []):
            if _map_run_status(run) != "failed":
                continue
            record = _map_run_to_failure(run)
            if pipeline_name:
                name_lower = pipeline_name.lower().replace(" ", "_")
                if name_lower not in record["pipeline_name"].lower():
                    continue
            failures.append(record)
        return failures
    except Exception as e:
        logger.warning("Databricks failure fetch failed: %s", e)
        return []


def get_clusters() -> list[dict]:
    clusters = get_clusters_from_table()
    if clusters:
        return clusters

    if not is_configured():
        return []

    try:
        data = _get("/api/2.0/clusters/list")
        cluster_list = data.get("clusters", [])
        return [_map_cluster_to_optimization(c) for c in cluster_list if c.get("cluster_source") != "JOB"]
    except Exception as e:
        logger.warning("Databricks clusters fetch failed: %s", e)
        return []


def get_connection_status() -> dict:
    if not is_configured():
        return {
            "configured": False,
            "connected": False,
            "host": DATABRICKS_HOST or None,
            "message": "Set DATABRICKS_HOST and DATABRICKS_TOKEN in .env",
            "mode": "mock_json",
        }

    try:
        pipelines = get_pipelines_from_table()
        failures = get_failures_from_table()
        clusters = get_clusters_from_table()

        if pipelines or failures or clusters:
            return {
                "configured": True,
                "connected": True,
                "host": DATABRICKS_HOST,
                "mode": "databricks_tables",
                "catalog": DATABRICKS_CATALOG,
                "schema": DATABRICKS_SCHEMA,
                "pipeline_rows": len(pipelines),
                "failure_rows": len(failures),
                "cluster_rows": len(clusters),
                "message": f"Reading from {DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA} tables",
            }

        _get("/api/2.0/clusters/list")
        runs = get_job_runs(limit=5)
        api_clusters = get_clusters()
        return {
            "configured": True,
            "connected": True,
            "host": DATABRICKS_HOST,
            "mode": "databricks_api",
            "job_runs_available": len(runs),
            "clusters_available": len(api_clusters),
            "message": "Connected via Databricks REST API (no tables found — run 01_create_tables.sql + seed script)",
        }
    except Exception as e:
        return {
            "configured": True,
            "connected": False,
            "host": DATABRICKS_HOST,
            "message": str(e),
            "mode": "error",
        }
