#!/usr/bin/env python3
"""Seed Databricks tables from local JSON mock data.

Usage:
    cd dataops-copilot
    py scripts/seed_databricks.py

Requires .env:
    USE_DATABRICKS=true
    DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
    DATABRICKS_TOKEN=your_token
    DATABRICKS_WAREHOUSE_ID=your_sql_warehouse_id
"""

import json
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / ".env")

from config import (  # noqa: E402
    DATA_DIR,
    DATABRICKS_CATALOG,
    DATABRICKS_HOST,
    DATABRICKS_SCHEMA,
    DATABRICKS_TOKEN,
    DATABRICKS_WAREHOUSE_ID,
)


def _sql_escape(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _execute_sql(statement: str) -> dict:
    url = f"{DATABRICKS_HOST.rstrip('/')}/api/2.0/sql/statements"
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}
    payload = {
        "warehouse_id": DATABRICKS_WAREHOUSE_ID,
        "statement": statement,
        "wait_timeout": "50s",
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    statement_id = result.get("statement_id")

    for _ in range(30):
        status_resp = requests.get(
            f"{url}/{statement_id}",
            headers=headers,
            timeout=30,
        )
        status_resp.raise_for_status()
        status_data = status_resp.json()
        state = status_data.get("status", {}).get("state")
        if state == "SUCCEEDED":
            return status_data
        if state in {"FAILED", "CANCELED", "CLOSED"}:
            raise RuntimeError(status_data)
        time.sleep(2)

    raise TimeoutError(f"SQL statement timed out: {statement[:80]}...")


def _table(name: str) -> str:
    return f"{DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}.{name}"


def _load_json(filename: str) -> list:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def seed_pipelines():
    rows = _load_json("pipelines.json")
    _execute_sql(f"DELETE FROM {_table('pipeline_runs')}")
    for row in rows:
        sql = f"""
        INSERT INTO {_table('pipeline_runs')} VALUES (
            {_sql_escape(row['pipeline_name'])},
            {_sql_escape(row['status'])},
            {_sql_escape(row.get('run_time'))},
            {_sql_escape(row.get('duration_minutes'))},
            {_sql_escape(row.get('error_message'))},
            {_sql_escape(row.get('cluster_id'))},
            {_sql_escape(row.get('cpu_usage'))},
            {_sql_escape(row.get('memory_usage'))},
            {_sql_escape(json.dumps(row.get('dependencies', [])))},
            {_sql_escape(row.get('last_success'))}
        )
        """
        _execute_sql(sql)
    print(f"Seeded {len(rows)} pipeline_runs rows")


def seed_failures():
    rows = _load_json("failures.json")
    _execute_sql(f"DELETE FROM {_table('failure_logs')}")
    for row in rows:
        sql = f"""
        INSERT INTO {_table('failure_logs')} VALUES (
            {_sql_escape(row['pipeline_name'])},
            {_sql_escape(row.get('failure_time'))},
            {_sql_escape(row.get('root_cause'))},
            {_sql_escape(row.get('error_details'))},
            {_sql_escape(row.get('cluster_logs'))},
            {_sql_escape(json.dumps(row.get('dependency_status', {})))},
            {_sql_escape(json.dumps(row.get('suggested_actions', [])))}
        )
        """
        _execute_sql(sql)
    print(f"Seeded {len(rows)} failure_logs rows")


def seed_clusters():
    rows = _load_json("clusters.json")
    _execute_sql(f"DELETE FROM {_table('cluster_metrics')}")
    for row in rows:
        sql = f"""
        INSERT INTO {_table('cluster_metrics')} VALUES (
            {_sql_escape(row['cluster_id'])},
            {_sql_escape(row.get('cluster_name'))},
            {_sql_escape(row.get('instance_type'))},
            {_sql_escape(row.get('recommended_type'))},
            {_sql_escape(row.get('avg_cpu_usage'))},
            {_sql_escape(row.get('avg_memory_usage'))},
            {_sql_escape(row.get('peak_cpu_usage'))},
            {_sql_escape(row.get('peak_memory_usage'))},
            {_sql_escape(row.get('monthly_cost_inr'))},
            {_sql_escape(row.get('estimated_savings_inr'))},
            {_sql_escape(json.dumps(row.get('jobs_running', [])))},
            {_sql_escape(row.get('recommendation'))}
        )
        """
        _execute_sql(sql)
    print(f"Seeded {len(rows)} cluster_metrics rows")


def main():
    if not all([DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID]):
        print("ERROR: Set DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID in .env")
        sys.exit(1)

    print(f"Seeding Databricks: {DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}")
    seed_pipelines()
    seed_failures()
    seed_clusters()
    print("Done! View tables in Databricks SQL Editor:")
    print(f"  SELECT * FROM {_table('pipeline_runs')};")


if __name__ == "__main__":
    main()
