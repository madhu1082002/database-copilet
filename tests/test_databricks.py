import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from services.databricks_service import _map_cluster_to_optimization, _map_run_status, _map_run_to_pipeline, _map_run_to_failure
from services.gemini_service import generate_response, _mock_response
from services.prompt_builder import build_context_for_intent, build_prompt
from services.response_cache import cache_clear, cache_get, cache_set, cache_size, make_cache_key
from services.source_extractor import extract_sources
from services import data_service


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
    assert pipeline["cpu_usage"] is None
    assert pipeline["memory_usage"] is None


def test_map_run_to_failure_uses_state_message():
    run = {
        "run_id": 9,
        "job_id": 3,
        "run_name": "customer_ingestion",
        "start_time": 1700000000000,
        "end_time": 1700000100000,
        "state": {"life_cycle_state": "TERMINATED", "result_state": "FAILED", "state_message": "API timeout"},
    }
    failure = _map_run_to_failure(run)
    assert failure["pipeline_name"] == "customer_ingestion"
    assert "API timeout" in failure["error_details"]


def test_cluster_api_mapping_does_not_invent_metrics():
    cluster = {
        "cluster_id": "abc",
        "cluster_name": "analytics_cluster",
        "node_type_id": "DS5_v2",
        "num_workers": 8,
        "state": "RUNNING",
    }
    mapped = _map_cluster_to_optimization(cluster)
    assert mapped["avg_cpu_usage"] is None
    assert mapped["avg_memory_usage"] is None
    assert mapped["estimated_savings_inr"] == 0
    assert mapped["metrics_available"] is False
    assert "not estimated" in mapped["recommendation"].lower() or "not returned" in mapped["recommendation"].lower()


@patch("services.databricks_service.get_pipelines_from_table", return_value=[])
@patch("services.databricks_service.is_configured", return_value=True)
@patch("services.databricks_service._get")
def test_get_job_runs(mock_get, _configured, _tables):
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


def test_response_cache_round_trip():
    cache_clear()
    key = make_cache_key("Did sales_etl run today?", "pipeline_status", "mock_json")
    assert cache_get(key) is None
    cache_set(key, {"response": "ok"}, ttl=60)
    assert cache_get(key)["response"] == "ok"
    assert cache_size() == 1
    cache_clear()
    assert cache_size() == 0


def test_cache_expires():
    cache_clear()
    key = make_cache_key("expired", "pipeline_status", "mock_json")
    cache_set(key, {"response": "old"}, ttl=-1)
    assert cache_get(key) is None


def test_extract_sources_from_failure_context():
    context = build_context_for_intent("failure_diagnosis", "customer_ingestion", data_service)
    sources = extract_sources("failure_diagnosis", context)
    assert any(s["name"] == "customer_ingestion" for s in sources)


def test_unknown_intent_context():
    context = build_context_for_intent("other", None, data_service)
    assert "pipelines" in context
    context = {"pipelines": [{"pipeline_name": "sales_etl", "status": "success"}]}
    prompt = build_prompt("Did sales_etl run today?", "pipeline_status", context)
    assert "DATA CONTEXT" in prompt
    assert "Do not invent" in prompt
    assert "sales_etl" in prompt


def test_mock_responses_cover_all_intents():
    status = _mock_response("pipeline_status", {"pipelines": [{"pipeline_name": "sales_etl", "status": "success", "run_time": "2026-07-01T00:00:00Z"}]})
    assert "sales_etl" in status
    empty_fail = _mock_response("failure_diagnosis", {"failures": []})
    assert "No failure records" in empty_fail
    empty_opt = _mock_response("optimization", {"optimization_opportunities": []})
    assert "No immediate optimization" in empty_opt
    other = _mock_response("unknown", {})
    assert "pipeline status" in other.lower()


def test_connection_status_unconfigured():
    from services.databricks_service import get_connection_status, is_configured

    assert is_configured() is False
    status = get_connection_status()
    assert status["configured"] is False
    assert status["mode"] == "mock_json"


def test_parse_helpers():
    from services.databricks_service import _parse_json_field, _to_float, _to_int, _format_timestamp

    assert _parse_json_field('["a"]', []) == ["a"]
    assert _parse_json_field("not-json", []) == []
    assert _parse_json_field(["a"], []) == ["a"]
    assert _to_int(None) == 0
    assert _to_int("12") == 12
    assert _to_float("") == 0.0
    assert _to_float("1.5") == 1.5
    assert _format_timestamp("2026-07-01 12:00:00").endswith("Z")


def test_table_mappers():
    from services.databricks_service import _map_table_cluster, _map_table_failure, _map_table_pipeline

    pipeline = _map_table_pipeline({"pipeline_name": "sales_etl", "status": "success", "cpu_usage": "12"})
    assert pipeline["source"] == "databricks_table"
    failure = _map_table_failure({"pipeline_name": "customer_ingestion", "root_cause": "timeout"})
    assert failure["source"] == "databricks_table"
    cluster = _map_table_cluster({"cluster_id": "c1", "estimated_savings_inr": "5000"})
    assert cluster["estimated_savings_inr"] == 5000


def test_generate_response_uses_mock_when_flagged():
    text = generate_response("prompt", "optimization", {"optimization_opportunities": []})
    assert "optimization" in text.lower() or "sized" in text.lower()


@patch("services.gemini_service.USE_MOCK_AI", False)
@patch("services.gemini_service.GEMINI_API_KEYS", ["fake-key"])
@patch("services.gemini_service._call_gemini", side_effect=RuntimeError("quota exceeded"))
def test_generate_response_falls_back_on_api_error(_call):
    text = generate_response(
        "prompt",
        "pipeline_status",
        {
            "summary": {"total_pipelines": 1, "success_count": 1, "failed_count": 0, "running_count": 0},
            "recent_failures": [],
        },
    )
    assert "Pipeline Dashboard Summary" in text or "Pipeline Status" in text
