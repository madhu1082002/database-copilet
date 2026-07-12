"""Detect ungrounded claims in AI responses vs retrieved context."""

from __future__ import annotations

import re

from qa.context_utils import extract_entities_from_context, extract_pipeline_mentions

INVENTED_PIPELINE_PATTERN = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")


def check_hallucination(
    response: str,
    context: dict,
    known_pipelines: set[str] | None = None,
) -> dict:
    """
    Compare response entities against retrieved context.

    Returns hallucination rate components for a single response.
    """
    allowed = extract_entities_from_context(context)
    response_lower = response.lower()

    if known_pipelines:
        mentioned_pipelines = extract_pipeline_mentions(response, known_pipelines)
    else:
        mentioned_pipelines = set(INVENTED_PIPELINE_PATTERN.findall(response_lower))

    hallucinated_pipelines = {
        name for name in mentioned_pipelines if name not in allowed and name not in _context_pipeline_names(context)
    }

    invented_status_claims = _find_invented_status_claims(response_lower, allowed)

    hallucinated = sorted(hallucinated_pipelines | invented_status_claims)
    total_claims = max(len(mentioned_pipelines) + len(invented_status_claims), 1)

    return {
        "hallucinated_entities": hallucinated,
        "hallucination_detected": bool(hallucinated),
        "mentioned_pipelines": sorted(mentioned_pipelines),
        "allowed_entities_count": len(allowed),
        "hallucination_rate": round(len(hallucinated) / total_claims, 4),
    }


def _context_pipeline_names(context: dict) -> set[str]:
    names: set[str] = set()

    def collect(obj):
        if isinstance(obj, dict):
            if "pipeline_name" in obj:
                names.add(obj["pipeline_name"].lower())
            for value in obj.values():
                collect(value)
        elif isinstance(obj, list):
            for item in obj:
                collect(item)

    collect(context)
    return names


def _find_invented_status_claims(response_lower: str, allowed: set[str]) -> set[str]:
    """Flag explicit success/failed claims on pipelines not in context."""
    invented: set[str] = set()
    for match in re.finditer(r"([a-z][a-z0-9_]+)\s+(is|was|has)\s+(success|failed|running)", response_lower):
        pipeline = match.group(1)
        status = match.group(3)
        if pipeline not in allowed and status not in allowed:
            invented.add(f"{pipeline}:{status}")
    return invented


def aggregate_hallucination_rate(results: list[dict]) -> float:
    if not results:
        return 0.0
    detected = sum(1 for r in results if r.get("hallucination_detected"))
    return round(detected / len(results), 4)
