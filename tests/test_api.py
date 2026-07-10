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
    assert data["total_pipelines"] >= 10


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


def test_intent_classifier():
    from services.intent_classifier import classify_intent

    assert classify_intent("Did Sales ETL run today?") == "pipeline_status"
    assert classify_intent("Why did Customer Sync fail?") == "failure_diagnosis"
    assert classify_intent("Can we reduce compute costs?") == "optimization"
