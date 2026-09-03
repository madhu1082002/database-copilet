import os
import sys

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
ROOT_DIR = os.path.dirname(FRONTEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import CORS_ORIGINS
from models.database import get_recent_responses, init_db, log_query, save_feedback
from qa.anomaly_detector import detect_output_anomaly
from services import data_service
from services import databricks_service
from services.gemini_service import generate_response
from services.intent_classifier import classify_intent_details
from services.prompt_builder import build_context_for_intent, build_prompt
from services.response_cache import cache_get, cache_set, make_cache_key
from services.source_extractor import extract_sources

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app, origins=CORS_ORIGINS.split(",") if CORS_ORIGINS != "*" else "*")

init_db()


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "DataOps Copilot",
        "data_source": data_service.get_data_source(),
    })


@app.route("/databricks/status")
def databricks_status():
    status = databricks_service.get_connection_status()
    status["data_source"] = data_service.get_data_source()
    return jsonify(status)


@app.route("/pipeline-status")
def pipeline_status():
    name = request.args.get("pipeline")
    pipelines = data_service.get_pipeline_status(name)
    return jsonify({"pipelines": pipelines, "count": len(pipelines), "data_source": data_service.get_data_source()})


@app.route("/failure-diagnosis")
def failure_diagnosis():
    name = request.args.get("pipeline")
    failures = data_service.get_failure_diagnosis(name)
    return jsonify({"failures": failures, "count": len(failures), "data_source": data_service.get_data_source()})


@app.route("/optimization")
def optimization():
    clusters = data_service.get_optimization_data()
    opportunities = [c for c in clusters if (c.get("estimated_savings_inr") or 0) > 0]
    total_savings = sum(c.get("estimated_savings_inr") or 0 for c in opportunities)
    return jsonify({
        "clusters": clusters,
        "optimization_opportunities": opportunities,
        "total_potential_savings_inr": total_savings,
        "data_source": data_service.get_data_source(),
        "savings_source": "stored_cluster_metrics",
    })


@app.route("/dashboard")
def dashboard():
    return jsonify(data_service.get_dashboard_summary())


@app.route("/query", methods=["POST"])
def query():
    body = request.get_json(silent=True) or {}
    user_query = (body.get("query") or "").strip()
    category_hint = body.get("category")

    if not user_query:
        return jsonify({"error": "Query is required"}), 400

    intent, confidence = classify_intent_details(user_query, category_hint)
    pipeline_name = data_service.extract_pipeline_name_from_query(user_query)
    context = build_context_for_intent(intent, pipeline_name, data_service)
    sources = extract_sources(intent, context)
    cache_key = make_cache_key(user_query, intent, data_service.get_data_source())
    cached_payload = cache_get(cache_key)
    cache_hit = cached_payload is not None

    if cache_hit:
        response_text = cached_payload["response"]
    else:
        prompt = build_prompt(user_query, intent, context)
        response_text = generate_response(prompt, intent, context)
        cache_set(cache_key, {"response": response_text})

    query_id = log_query(user_query, category_hint or intent, response_text, intent)
    anomaly = detect_output_anomaly(get_recent_responses(20))

    return jsonify({
        "query": user_query,
        "query_id": query_id,
        "intent": intent,
        "pipeline": pipeline_name,
        "response": response_text,
        "category": intent,
        "confidence": confidence,
        "sources": sources,
        "cached": cache_hit,
        "anomaly": anomaly,
    })


@app.route("/feedback", methods=["POST"])
def feedback():
    body = request.get_json(silent=True) or {}
    query_id = body.get("query_id")
    feedback_value = body.get("feedback")

    if not query_id or feedback_value not in ("up", "down"):
        return jsonify({"error": "query_id and feedback (up/down) are required"}), 400

    try:
        query_id = int(query_id)
    except (TypeError, ValueError):
        return jsonify({"error": "query_id must be an integer"}), 400

    updated = save_feedback(query_id, feedback_value)
    if not updated:
        return jsonify({"error": "query_id not found"}), 404
    return jsonify({"status": "ok", "query_id": query_id, "feedback": feedback_value})


@app.route("/qa/anomaly")
def qa_anomaly():
    return jsonify(detect_output_anomaly(get_recent_responses(20)))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
