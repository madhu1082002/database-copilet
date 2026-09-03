import json
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from google import genai

from config import GEMINI_API_KEYS, GEMINI_MODEL, GEMINI_TIMEOUT_SECONDS, USE_MOCK_AI

logger = logging.getLogger(__name__)

_active_key_index = 0


def _call_gemini(api_key: str, prompt: str) -> str:
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    text = response.text or ""

    if hasattr(response, "thought") and response.thought:
        text += f"\n\n--- Model Thought Process ---\n{response.thought}"

    return text


def generate_response(prompt: str, intent: str, context_data: dict) -> str:
    global _active_key_index

    if USE_MOCK_AI:
        return _mock_response(intent, context_data)

    if not GEMINI_API_KEYS:
        return _mock_response(intent, context_data)

    keys_to_try = len(GEMINI_API_KEYS)

    for attempt in range(keys_to_try):
        key_index = (_active_key_index + attempt) % keys_to_try
        api_key = GEMINI_API_KEYS[key_index]

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_call_gemini, api_key, prompt)
                text = future.result(timeout=GEMINI_TIMEOUT_SECONDS)
            if text:
                _active_key_index = key_index
                if attempt > 0:
                    logger.info("Switched to Gemini API key #%d", key_index + 1)
                return text
        except FuturesTimeout:
            logger.warning("Gemini 2.5 Flash key #%d timed out after %ss", key_index + 1, GEMINI_TIMEOUT_SECONDS)
            if attempt < keys_to_try - 1:
                continue
        except Exception as e:
            logger.warning("Gemini 2.5 Flash key #%d failed: %s", key_index + 1, e)
            if attempt < keys_to_try - 1:
                continue

    _active_key_index = (_active_key_index + 1) % keys_to_try
    logger.error("All Gemini API keys exhausted for gemini-2.5-flash. Using rule-based response.")
    return _mock_response(intent, context_data)


def _mock_response(intent: str, context: dict) -> str:
    if intent == "pipeline_status":
        return _mock_pipeline_status(context)
    if intent == "failure_diagnosis":
        return _mock_failure_diagnosis(context)
    if intent == "optimization":
        return _mock_optimization(context)
    return "I can help with pipeline status, failure diagnosis, and optimization queries."


def _mock_pipeline_status(context: dict) -> str:
    pipelines = context.get("pipelines") or context.get("summary", {}).get("pipelines", [])
    if not pipelines and "summary" in context:
        s = context["summary"]
        return (
            f"**Pipeline Dashboard Summary**\n\n"
            f"- Total pipelines: {s['total_pipelines']}\n"
            f"- Successful: {s['success_count']}\n"
            f"- Failed: {s['failed_count']}\n"
            f"- Running: {s['running_count']}\n\n"
            f"Failed pipelines in the last 24h: "
            + ", ".join(p["pipeline_name"] for p in context.get("recent_failures", []))
        )

    lines = ["**Pipeline Status**\n"]
    for p in pipelines:
        status_icon = {"success": "✅", "failed": "❌", "partial_failure": "⚠️", "running": "🔄"}.get(p["status"], "•")
        lines.append(f"{status_icon} **{p['pipeline_name']}**: {p['status']} (ran at {p['run_time']})")
        if p.get("error_message"):
            lines.append(f"   Error: {p['error_message']}")
    return "\n".join(lines)


def _mock_failure_diagnosis(context: dict) -> str:
    failures = context.get("failures", [])
    if not failures:
        return "No failure records found for the specified pipeline. All recent runs may have succeeded."

    f = failures[0]
    actions = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(f.get("suggested_actions", [])))
    deps = json.dumps(f.get("dependency_status", {}), indent=2)

    return (
        f"**Failure Diagnosis: {f['pipeline_name']}**\n\n"
        f"**Root Cause:** {f['root_cause']}\n\n"
        f"**Error Details:** {f['error_details']}\n\n"
        f"**Cluster Logs:** {f['cluster_logs']}\n\n"
        f"**Dependency Status:**\n```\n{deps}\n```\n\n"
        f"**Suggested Actions:**\n{actions}"
    )


def _mock_optimization(context: dict) -> str:
    opportunities = context.get("optimization_opportunities", [])
    if not opportunities:
        clusters = context.get("clusters", [])
        return "All clusters appear appropriately sized. No immediate optimization opportunities detected."

    lines = ["**Optimization Recommendations**\n"]
    total_savings = 0
    for c in opportunities:
        savings = c.get("estimated_savings_inr") or 0
        total_savings += savings
        cpu = c.get("avg_cpu_usage")
        cpu_line = f"- Average CPU: {cpu}%\n" if cpu is not None else "- Average CPU: not available in retrieved metrics\n"
        recommended = c.get("recommended_type") or "n/a"
        lines.append(
            f"**{c.get('cluster_name') or c.get('cluster_id')}** is underutilized.\n"
            f"{cpu_line}"
            f"- Current: {c.get('instance_type')} → Recommended: {recommended}\n"
            f"- Estimated monthly savings: ₹{savings:,}\n"
            f"- {c.get('recommendation')}\n"
        )
    lines.append(f"\n**Total potential monthly savings: ₹{total_savings:,}**")
    return "\n".join(lines)
