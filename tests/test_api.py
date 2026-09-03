import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert "data_source" in data


def test_databricks_status(client):
    res = client.get("/databricks/status")
    assert res.status_code == 200
    data = res.get_json()
    assert "configured" in data
    assert data.get("data_source", "mock_json") == "mock_json"


def test_pipeline_status(client):
    res = client.get("/pipeline-status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] > 0
    assert "pipelines" in data


def test_pipeline_status_filter(client):
    res = client.get("/pipeline-status?pipeline=customer_ingestion")
    assert res.status_code == 200
    data = res.get_json()
    assert any("customer_ingestion" in p["pipeline_name"] for p in data["pipelines"])


def test_failure_diagnosis(client):
    res = client.get("/failure-diagnosis")
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] > 0


def test_optimization(client):
    res = client.get("/optimization")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_potential_savings_inr" in data
    assert data["total_potential_savings_inr"] > 0


def test_dashboard(client):
    res = client.get("/dashboard")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_pipelines" in data
    assert data["total_pipelines"] >= 50


def test_query_pipeline_status(client):
    res = client.post("/query", json={"query": "Did sales_etl run today?"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["intent"] == "pipeline_status"
    assert "sales_etl" in data["response"].lower() or "success" in data["response"].lower()


def test_query_failure_diagnosis(client):
    res = client.post("/query", json={"query": "Why did customer_ingestion fail?"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["intent"] == "failure_diagnosis"
    assert "customer_ingestion" in data["response"].lower()


def test_query_optimization(client):
    res = client.post("/query", json={"query": "Can we reduce compute costs?"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["intent"] == "optimization"
    assert "savings" in data["response"].lower() or "cpu" in data["response"].lower()


def test_query_empty(client):
    res = client.post("/query", json={"query": ""})
    assert res.status_code == 400


def test_query_missing_body(client):
    res = client.post("/query", json={})
    assert res.status_code == 400


def test_query_malformed_json(client):
    res = client.post("/query", data="not-json", content_type="application/json")
    assert res.status_code == 400


def test_query_returns_query_id_confidence_and_sources(client):
    from services.response_cache import cache_clear

    cache_clear()
    res = client.post("/query", json={"query": "Show me the status of unique_pipeline_probe_query"})
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data["query_id"], int)
    assert 0 < data["confidence"] <= 1
    assert isinstance(data["sources"], list)
    assert data["cached"] is False


def test_query_cache_hit(client):
    from services.response_cache import cache_clear

    cache_clear()
    first = client.post("/query", json={"query": "Did sales_etl run today?"}).get_json()
    second = client.post("/query", json={"query": "Did sales_etl run today?"}).get_json()
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["response"] == first["response"]


def test_feedback_round_trip(client):
    created = client.post("/query", json={"query": "Why did customer_ingestion fail?"}).get_json()
    query_id = created["query_id"]
    res = client.post("/feedback", json={"query_id": query_id, "feedback": "up"})
    assert res.status_code == 200
    from models.database import get_query_by_id

    row = get_query_by_id(query_id)
    assert row["feedback"] == "up"


def test_feedback_missing_fields(client):
    res = client.post("/feedback", json={"query_id": 1})
    assert res.status_code == 400


def test_feedback_invalid_id(client):
    res = client.post("/feedback", json={"query_id": "abc", "feedback": "up"})
    assert res.status_code == 400
    res = client.post("/feedback", json={"query_id": 999999, "feedback": "down"})
    assert res.status_code == 404


def test_index_serves_ui(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"DataOps Copilot" in res.data


def test_qa_anomaly_endpoint(client):
    res = client.get("/qa/anomaly")
    assert res.status_code == 200
    data = res.get_json()
    assert "anomaly" in data
    assert "no_data_rate" in data


def test_query_response_time_under_10s(client):
    import time

    start = time.perf_counter()
    res = client.post("/query", json={"query": "Can we reduce compute costs?"})
    elapsed = time.perf_counter() - start
    assert res.status_code == 200
    assert elapsed < 10


def test_intent_classifier():
    from services.intent_classifier import classify_intent, classify_intent_details

    assert classify_intent("Did Sales ETL run today?") == "pipeline_status"
    assert classify_intent("Why did Customer Sync fail?") == "failure_diagnosis"
    assert classify_intent("Can we reduce compute costs?") == "optimization"
    intent, confidence = classify_intent_details("Why did Customer Sync fail?")
    assert intent == "failure_diagnosis"
    assert confidence >= 0.5
    hinted, hinted_conf = classify_intent_details("hello", "optimization")
    assert hinted == "optimization"
    assert hinted_conf == 1.0
    unknown, unknown_conf = classify_intent_details("hello there")
    assert unknown == "pipeline_status"
    assert unknown_conf == 0.4
