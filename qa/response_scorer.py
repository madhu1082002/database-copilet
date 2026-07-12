"""Score AI responses for intent match, grounding, and completeness."""

from __future__ import annotations

import json
import logging

from qa.context_utils import extract_entities_from_context, extract_pipeline_mentions
from qa.hallucination_checker import check_hallucination

logger = logging.getLogger(__name__)

GEMINI_SCORING_PROMPT = """You are a QA evaluator for a DataOps AI assistant.
Score the assistant response against the ground-truth context.

Return ONLY valid JSON with this shape:
{{
  "accuracy": <1-5>,
  "completeness": <1-5>,
  "clarity": <1-5>,
  "grounding": <1-5>,
  "overall": <1-5>,
  "notes": "<one sentence>"
}}

Scoring criteria:
- accuracy: facts match the context
- completeness: answers the engineer's question
- clarity: readable and actionable
- grounding: no invented pipeline names, statuses, or metrics
- overall: holistic quality

ENGINEER QUERY: {query}
EXPECTED INTENT: {intent}

DATA CONTEXT:
{context}

ASSISTANT RESPONSE:
{response}
"""


def score_response_rule_based(
    query: str,
    response: str,
    expected_intent: str,
    actual_intent: str,
    context: dict,
    known_pipelines: set[str] | None = None,
) -> dict:
    """Deterministic scoring — works offline without Gemini."""
    hallucination = check_hallucination(response, context, known_pipelines)
    allowed = extract_entities_from_context(context)

    intent_match = expected_intent == actual_intent
    grounding_score = 100.0 if not hallucination["hallucination_detected"] else max(
        0.0, 100.0 - hallucination["hallucination_rate"] * 100
    )

    completeness_score = _completeness_score(query, response, expected_intent, context)
    clarity_score = _clarity_score(response)

    overall = round((grounding_score * 0.4 + completeness_score * 0.35 + clarity_score * 0.25), 2)

    return {
        "intent_match": intent_match,
        "expected_intent": expected_intent,
        "actual_intent": actual_intent,
        "grounding_score": grounding_score,
        "completeness_score": completeness_score,
        "clarity_score": clarity_score,
        "overall_score": overall,
        "hallucination": hallucination,
        "gemini_scores": None,
    }


def score_response_with_gemini(
    query: str,
    response: str,
    expected_intent: str,
    actual_intent: str,
    context: dict,
    known_pipelines: set[str] | None = None,
) -> dict:
    """Rule-based score plus optional Gemini quality rubric."""
    base = score_response_rule_based(
        query, response, expected_intent, actual_intent, context, known_pipelines
    )

    try:
        from config import GEMINI_API_KEYS, USE_MOCK_AI
        from services.gemini_service import _call_gemini

        if USE_MOCK_AI or not GEMINI_API_KEYS:
            return base

        prompt = GEMINI_SCORING_PROMPT.format(
            query=query,
            intent=expected_intent,
            context=json.dumps(context, indent=2, default=str)[:8000],
            response=response[:4000],
        )
        raw = _call_gemini(GEMINI_API_KEYS[0], prompt)
        gemini_scores = _parse_gemini_json(raw)
        base["gemini_scores"] = gemini_scores
        if gemini_scores and "overall" in gemini_scores:
            base["overall_score"] = round(
                (base["overall_score"] * 0.5 + (gemini_scores["overall"] / 5 * 100) * 0.5),
                2,
            )
    except Exception as exc:
        logger.warning("Gemini response scoring skipped: %s", exc)

    return base


def _completeness_score(query: str, response: str, intent: str, context: dict) -> float:
    response_lower = response.lower()
    if len(response.strip()) < 20:
        return 20.0

    if intent == "pipeline_status":
        if any(token in response_lower for token in ("status", "success", "failed", "running", "pipeline")):
            return 85.0
        return 50.0

    if intent == "failure_diagnosis":
        checks = ("root cause", "error", "suggested", "action", "fail")
        hits = sum(1 for token in checks if token in response_lower)
        return min(100.0, 40.0 + hits * 15)

    if intent == "optimization":
        checks = ("cpu", "cluster", "savings", "cost", "recommend")
        hits = sum(1 for token in checks if token in response_lower)
        savings_in_context = any(
            str(c.get("estimated_savings_inr", 0)) in response
            for c in context.get("optimization_opportunities", context.get("clusters", []))
        )
        bonus = 15 if savings_in_context or "₹" in response else 0
        return min(100.0, 35.0 + hits * 12 + bonus)

    mentioned = extract_pipeline_mentions(response, None)
    allowed = extract_entities_from_context(context)
    if mentioned and mentioned.issubset(allowed):
        return 75.0
    return 60.0


def _clarity_score(response: str) -> float:
    text = response.strip()
    if not text:
        return 0.0
    score = 70.0
    if any(marker in text for marker in ("**", "- ", "1.", "\n")):
        score += 15.0
    if len(text) > 800:
        score -= 10.0
    return min(100.0, max(30.0, score))


def _parse_gemini_json(raw: str) -> dict | None:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
