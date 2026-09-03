import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from services import data_service
from services import databricks_service as dbs
from services.gemini_service import _call_gemini
from qa.run_ai_qa import run_qa_suite


def _sql_success(columns, rows):
    post = MagicMock()
    post.raise_for_status = MagicMock()
    post.json.return_value = {"statement_id": "s1"}
    get = MagicMock()
    get.raise_for_status = MagicMock()
    get.json.return_value = {
        "status": {"state": "SUCCEEDED"},
        "manifest": {"schema": {"columns": [{"name": c} for c in columns]}},
        "result": {"data_array": rows},
    }
    return post, get


@patch("services.databricks_service.has_sql_warehouse", return_value=True)
@patch("services.databricks_service.DATABRICKS_HOST", "https://example.cloud.databricks.com")
@patch("services.databricks_service.DATABRICKS_TOKEN", "tok")
@patch("services.databricks_service.DATABRICKS_WAREHOUSE_ID", "wh")
@patch("services.databricks_service.requests.get")
@patch("services.databricks_service.requests.post")
def test_execute_sql_and_table_reads(mock_post, mock_get, *_args):
    mock_post.return_value.raise_for_status = MagicMock()
    mock_post.return_value.json.return_value = {"statement_id": "s1"}
    mock_get.return_value.raise_for_status = MagicMock()
    mock_get.return_value.json.return_value = {
        "status": {"state": "SUCCEEDED"},
        "manifest": {"schema": {"columns": [{"name": "pipeline_name"}, {"name": "status"}]}},
        "result": {"data_array": [["sales_etl", "success"]]},
    }
    rows = dbs.execute_sql("SELECT 1")
    assert rows[0]["pipeline_name"] == "sales_etl"
    pipelines = dbs.get_pipelines_from_table()
    assert pipelines[0]["pipeline_name"] == "sales_etl"


@patch("services.databricks_service.has_sql_warehouse", return_value=True)
@patch("services.databricks_service.DATABRICKS_HOST", "https://example.cloud.databricks.com")
@patch("services.databricks_service.DATABRICKS_TOKEN", "tok")
@patch("services.databricks_service.execute_sql", side_effect=RuntimeError("fail"))
def test_table_reads_return_empty_on_error(_sql, *_args):
    assert dbs.get_pipelines_from_table() == []
    assert dbs.get_failures_from_table() == []
    assert dbs.get_clusters_from_table() == []


@patch("services.databricks_service.get_pipelines_from_table", return_value=[])
@patch("services.databricks_service.is_configured", return_value=True)
@patch("services.databricks_service._get", side_effect=RuntimeError("network"))
def test_get_job_runs_api_error(_get, *_args):
    assert dbs.get_job_runs() == []


@patch("services.databricks_service.get_failures_from_table", return_value=[])
@patch("services.databricks_service.is_configured", return_value=True)
@patch("services.databricks_service._get")
def test_get_failure_records_from_jobs_api(mock_get, *_args):
    mock_get.return_value = {
        "runs": [
            {
                "run_id": 1,
                "job_id": 10,
                "run_name": "customer_ingestion",
                "start_time": 1700000000000,
                "state": {"life_cycle_state": "TERMINATED", "result_state": "FAILED", "state_message": "Timeout"},
            },
            {
                "run_id": 2,
                "job_id": 11,
                "run_name": "sales_etl",
                "start_time": 1700000000000,
                "state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"},
            },
        ]
    }
    failures = dbs.get_failure_records("customer")
    assert len(failures) == 1
    assert failures[0]["pipeline_name"] == "customer_ingestion"


@patch("services.databricks_service.get_clusters_from_table", return_value=[])
@patch("services.databricks_service.is_configured", return_value=True)
@patch("services.databricks_service._get")
def test_get_clusters_from_api(mock_get, *_args):
    mock_get.return_value = {
        "clusters": [
            {"cluster_id": "c1", "cluster_name": "analytics", "node_type_id": "DS3_v2", "state": "RUNNING", "cluster_source": "UI"},
            {"cluster_id": "job1", "cluster_source": "JOB"},
        ]
    }
    clusters = dbs.get_clusters()
    assert len(clusters) == 1
    assert clusters[0]["estimated_savings_inr"] == 0


@patch("services.databricks_service.is_configured", return_value=True)
@patch("services.databricks_service.get_pipelines_from_table", return_value=[{"pipeline_name": "p"}])
@patch("services.databricks_service.get_failures_from_table", return_value=[{"pipeline_name": "p"}])
@patch("services.databricks_service.get_clusters_from_table", return_value=[{"cluster_id": "c"}])
def test_connection_status_tables(_c, _f, _p, _cfg):
    status = dbs.get_connection_status()
    assert status["connected"] is True
    assert status["mode"] == "databricks_tables"


@patch("services.databricks_service.is_configured", return_value=True)
@patch("services.databricks_service.get_pipelines_from_table", return_value=[])
@patch("services.databricks_service.get_failures_from_table", return_value=[])
@patch("services.databricks_service.get_clusters_from_table", return_value=[])
@patch("services.databricks_service._get", return_value={"clusters": []})
@patch("services.databricks_service.get_job_runs", return_value=[])
@patch("services.databricks_service.get_clusters", return_value=[])
def test_connection_status_api_mode(*_args):
    status = dbs.get_connection_status()
    assert status["mode"] == "databricks_api"


@patch("services.databricks_service.is_configured", return_value=True)
@patch("services.databricks_service.get_pipelines_from_table", side_effect=RuntimeError("boom"))
def test_connection_status_error(_tables, _cfg):
    status = dbs.get_connection_status()
    assert status["mode"] == "error"
    assert status["connected"] is False


@patch("services.data_service._using_databricks", return_value=True)
@patch("services.data_service.databricks_service.has_sql_warehouse", return_value=True)
@patch("services.data_service.databricks_service.get_pipelines_from_table", return_value=[{"pipeline_name": "x"}])
def test_data_source_tables(_t, _w, _u):
    assert data_service.get_data_source() == "databricks_tables"


@patch("services.data_service._using_databricks", return_value=True)
@patch("services.data_service.databricks_service.get_job_runs", return_value=[{"pipeline_name": "live_job", "status": "success"}])
def test_pipelines_from_databricks(_runs, _using):
    rows = data_service.get_all_pipelines()
    assert rows[0]["pipeline_name"] == "live_job"


@patch("services.data_service._using_databricks", return_value=True)
@patch("services.data_service.databricks_service.get_failed_runs", return_value=[{"pipeline_name": "bad", "status": "failed"}])
def test_failed_from_databricks(_failed, _using):
    assert data_service.get_failed_pipelines()[0]["pipeline_name"] == "bad"


@patch("services.data_service._using_databricks", return_value=True)
@patch("services.data_service.databricks_service.get_failure_records", return_value=[{"pipeline_name": "bad"}])
def test_failures_from_databricks(_rec, _using):
    assert data_service.get_failure_diagnosis()[0]["pipeline_name"] == "bad"


@patch("services.data_service._using_databricks", return_value=True)
@patch("services.data_service.databricks_service.get_clusters", return_value=[{"cluster_id": "c1", "estimated_savings_inr": 0}])
def test_clusters_from_databricks(_clusters, _using):
    assert data_service.get_optimization_data()[0]["cluster_id"] == "c1"


@patch("services.gemini_service.genai.Client")
def test_call_gemini(mock_client):
    response = MagicMock()
    response.text = "grounded answer"
    response.thought = None
    mock_client.return_value.models.generate_content.return_value = response
    assert _call_gemini("key", "prompt") == "grounded answer"


def test_run_qa_suite_skips_empty_query():
    report = run_qa_suite([{"id": "empty", "query": "   ", "expected_intent": "pipeline_status"}], use_gemini_scoring=False)
    assert report["skipped"] == 1
    assert report["evaluated"] == 0


@patch("services.data_service._using_databricks", return_value=True)
@patch("services.data_service.databricks_service.has_sql_warehouse", return_value=False)
def test_data_source_api_mode(_w, _u):
    assert data_service.get_data_source() == "databricks"


def test_extract_sources_optimization_without_opportunities():
    from services.source_extractor import extract_sources

    sources = extract_sources(
        "optimization",
        {"clusters": [{"cluster_name": "analytics_cluster", "estimated_savings_inr": 0}]},
    )
    assert any(s["name"] == "analytics_cluster" for s in sources)
    assert dbs.execute_sql("SELECT 1") == []


@patch("services.databricks_service.get_failures_from_table", return_value=[])
@patch("services.databricks_service.is_configured", return_value=False)
def test_failure_records_unconfigured(_cfg, _table):
    assert dbs.get_failure_records() == []


@patch("services.databricks_service.get_clusters_from_table", return_value=[])
@patch("services.databricks_service.is_configured", return_value=False)
def test_clusters_unconfigured(_cfg, _table):
    assert dbs.get_clusters() == []


@patch("services.databricks_service.has_sql_warehouse", return_value=True)
@patch("services.databricks_service.DATABRICKS_HOST", "https://example.cloud.databricks.com")
@patch("services.databricks_service.DATABRICKS_TOKEN", "tok")
@patch("services.databricks_service.requests.get")
@patch("services.databricks_service.requests.post")
def test_execute_sql_failed_state(mock_post, mock_get, *_args):
    mock_post.return_value.raise_for_status = MagicMock()
    mock_post.return_value.json.return_value = {"statement_id": "s1"}
    mock_get.return_value.raise_for_status = MagicMock()
    mock_get.return_value.json.return_value = {
        "status": {"state": "FAILED", "error": {"message": "syntax"}},
    }
    try:
        dbs.execute_sql("SELECT bad")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "syntax" in str(exc)
