import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qa.anomaly_detector import detect_output_anomaly, is_no_data_response


def test_is_no_data_response():
    assert is_no_data_response("")
    assert is_no_data_response("No failure records found for the specified pipeline.")
    assert is_no_data_response("All clusters appear appropriately sized. No immediate optimization opportunities detected.")
    assert not is_no_data_response("customer_ingestion failed because the upstream API timed out.")


def test_anomaly_not_flagged_for_mixed_responses():
    recent = [
        "sales_etl succeeded",
        "No failure records found",
        "analytics_cluster is underutilized",
        "inventory_sync is running",
        "customer_ingestion failed",
    ]
    result = detect_output_anomaly(recent, threshold=0.9, min_samples=5)
    assert result["anomaly"] is False


def test_anomaly_flagged_when_almost_all_no_data():
    recent = ["No data available"] * 9 + ["sales_etl succeeded"]
    result = detect_output_anomaly(recent, threshold=0.9, min_samples=5)
    assert result["anomaly"] is True
    assert result["reason"] == "high_no_data_rate"


def test_anomaly_empty_history():
    result = detect_output_anomaly([])
    assert result["anomaly"] is False
    assert result["sample_size"] == 0
