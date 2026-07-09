import json

SYSTEM_INSTRUCTIONS = """You are DataOps Copilot, a GenAI-powered assistant for data engineering teams.
You help engineers monitor pipelines, diagnose failures, and find optimization opportunities.

CRITICAL RULES:
- Only use facts from the DATA CONTEXT provided below. Do not invent pipeline names, statuses, or metrics.
- If data is missing, say so clearly.
- Be concise but actionable. Use bullet points for suggested actions.
- Include specific numbers (CPU %, savings in ₹) when available in the data.
- Format responses clearly with headers when appropriate."""


def build_prompt(query: str, intent: str, context_data: dict) -> str:
    context_json = json.dumps(context_data, indent=2, default=str)

    intent_guidance = {
        "pipeline_status": "Answer about pipeline run status, timestamps, and success/failure counts.",
        "failure_diagnosis": "Diagnose the failure root cause. Include error details, cluster logs, and suggested actions.",
        "optimization": "Analyze cluster utilization and recommend cost optimizations with estimated ₹ savings.",
    }

    return f"""{SYSTEM_INSTRUCTIONS}

QUERY CATEGORY: {intent.replace("_", " ").title()}
TASK: {intent_guidance.get(intent, "Answer the engineer's question using the data below.")}

ENGINEER QUERY: {query}

DATA CONTEXT:
{context_json}

Provide a helpful, grounded response:"""


def build_context_for_intent(intent: str, pipeline_name: str | None, data_service) -> dict:
    if intent == "pipeline_status":
        if pipeline_name:
            return {"pipelines": data_service.get_pipeline_status(pipeline_name)}
        return {
            "summary": data_service.get_dashboard_summary(),
            "recent_failures": data_service.get_failed_pipelines(),
        }

    if intent == "failure_diagnosis":
        failures = data_service.get_failure_diagnosis(pipeline_name)
        related_pipelines = data_service.get_pipeline_status(pipeline_name) if pipeline_name else []
        return {"failures": failures, "pipeline_runs": related_pipelines}

    if intent == "optimization":
        clusters = data_service.get_optimization_data()
        undersized = [c for c in clusters if c.get("estimated_savings_inr", 0) > 0]
        return {"clusters": clusters, "optimization_opportunities": undersized}

    return {"pipelines": data_service.get_all_pipelines()}
