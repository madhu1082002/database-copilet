import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "backend" / "data"
TEST_QUERIES_FILE = ROOT / "data" / "test_queries.json"


def test_mock_pipeline_count():
    with open(DATA_DIR / "pipelines.json", encoding="utf-8") as f:
        pipelines = json.load(f)
    assert len(pipelines) >= 50, f"Expected 50+ pipeline scenarios, got {len(pipelines)}"


def test_mock_failure_count():
    with open(DATA_DIR / "failures.json", encoding="utf-8") as f:
        failures = json.load(f)
    assert len(failures) >= 10


def test_mock_cluster_count():
    with open(DATA_DIR / "clusters.json", encoding="utf-8") as f:
        clusters = json.load(f)
    assert len(clusters) >= 10


def test_all_status_scenarios_present():
    with open(DATA_DIR / "pipelines.json", encoding="utf-8") as f:
        pipelines = json.load(f)
    statuses = {p["status"] for p in pipelines}
    assert {"success", "failed", "partial_failure", "running"}.issubset(statuses)


def test_failed_pipelines_have_failure_records():
    with open(DATA_DIR / "pipelines.json", encoding="utf-8") as f:
        pipelines = json.load(f)
    with open(DATA_DIR / "failures.json", encoding="utf-8") as f:
        failures = json.load(f)

    failed_names = {
        p["pipeline_name"]
        for p in pipelines
        if p["status"] in ("failed", "partial_failure")
    }
    failure_names = {f["pipeline_name"] for f in failures}
    missing = failed_names - failure_names
    assert not missing, f"Missing failure records for: {sorted(missing)}"


def test_test_queries_file_has_50_plus():
    assert TEST_QUERIES_FILE.exists(), "Run scripts/build_test_queries.py first"
    with open(TEST_QUERIES_FILE, encoding="utf-8") as f:
        payload = json.load(f)
    queries = payload.get("queries", [])
    assert len(queries) >= 50, f"Expected 50+ test queries, got {len(queries)}"


def test_test_queries_cover_all_intents():
    with open(TEST_QUERIES_FILE, encoding="utf-8") as f:
        payload = json.load(f)
    intents = {q["expected_intent"] for q in payload["queries"]}
    assert intents == {"pipeline_status", "failure_diagnosis", "optimization"}
