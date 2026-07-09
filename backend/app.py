import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import CORS_ORIGINS
from models.database import init_db, log_query, save_feedback
from services import data_service
from services.gemini_service import generate_response
from services.intent_classifier import classify_intent
from services.prompt_builder import build_context_for_intent, build_prompt

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app, origins=CORS_ORIGINS.split(",") if CORS_ORIGINS != "*" else "*")

init_db()


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "DataOps Copilot"})


@app.route("/pipeline-status")
def pipeline_status():
    name = request.args.get("pipeline")
    pipelines = data_service.get_pipeline_status(name)
    return jsonify({"pipelines": pipelines, "count": len(pipelines)})


@app.route("/failure-diagnosis")
def failure_diagnosis():
    name = request.args.get("pipeline")
    failures = data_service.get_failure_diagnosis(name)
    return jsonify({"failures": failures, "count": len(failures)})


@app.route("/optimization")
def optimization():
    clusters = data_service.get_optimization_data()
    opportunities = [c for c in clusters if c.get("estimated_savings_inr", 0) > 0]
    total_savings = sum(c.get("estimated_savings_inr", 0) for c in opportunities)
    return jsonify({
        "clusters": clusters,
        "optimization_opportunities": opportunities,
        "total_potential_savings_inr": total_savings,
    })


@app.route("/dashboard")
def dashboard():
    return jsonify(data_service.get_dashboard_summary())


@app.route("/query", methods=["POST"])
def query():
    body = request.get_json(silent=True) or {}
    user_query = body.get("query", "").strip()
    category_hint = body.get("category")

    if not user_query:
        return jsonify({"error": "Query is required"}), 400

    intent = classify_intent(user_query, category_hint)
    pipeline_name = data_service.extract_pipeline_name_from_query(user_query)
    context = build_context_for_intent(intent, pipeline_name, data_service)
    prompt = build_prompt(user_query, intent, context)
    response_text = generate_response(prompt, intent, context)

    log_query(user_query, category_hint or intent, response_text, intent)

    return jsonify({
        "query": user_query,
        "intent": intent,
        "pipeline": pipeline_name,
        "response": response_text,
        "category": intent,
    })


@app.route("/feedback", methods=["POST"])
def feedback():
    body = request.get_json(silent=True) or {}
    query_id = body.get("query_id")
    feedback_value = body.get("feedback")

    if not query_id or feedback_value not in ("up", "down"):
        return jsonify({"error": "query_id and feedback (up/down) are required"}), 400

    save_feedback(query_id, feedback_value)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
