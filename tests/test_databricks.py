import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.databricks_service import _map_run_status, _map_run_to_pipeline


def test_map_run_status_success():
    run = {"state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"}}
    assert _map_run_status(run) == "success"


def test_map_run_status_failed():
    run = {"state": {"life_cycle_state": "TERMINATED", "result_state": "FAILED"}}
    assert _map_run_status(run) == "failed"


def test_map_run_status_running():
    run = {"state": {"life_cycle_state": "RUNNING"}}
    assert _map_run_status(run) == "running"


def test_map_run_to_pipeline():
    run = {
        "run_id": 101,
        "job_id": 42,
        "run_name": "sales_etl",
        "start_time": 1700000000000,
        "end_time": 1700003600000,
        "state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"},
    }
    pipeline = _map_run_to_pipeline(run)
    assert pipeline["pipeline_name"] == "sales_etl"
    assert pipeline["status"] == "success"
    assert pipeline["source"] == "databricks_jobs_api"


@patch("services.databricks_service.is_configured", return_value=True)
@patch("services.databricks_service._get")
def test_get_job_runs(mock_get, _configured):
    mock_get.return_value = {
        "runs": [
            {
                "run_id": 1,
                "job_id": 10,
                "run_name": "customer_ingestion",
                "start_time": 1700000000000,
                "state": {"life_cycle_state": "TERMINATED", "result_state": "FAILED", "state_message": "Timeout"},
            }
        ]
    }
    from services.databricks_service import get_job_runs

    runs = get_job_runs()
    assert len(runs) == 1
    assert runs[0]["pipeline_name"] == "customer_ingestion"
    assert runs[0]["status"] == "failed"
