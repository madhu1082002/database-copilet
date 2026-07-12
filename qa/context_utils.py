"""Extract entities from RAG context and AI responses for grounding checks."""

from __future__ import annotations

import re
from typing import Any

PIPELINE_PATTERN = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
CLUSTER_PATTERN = re.compile(r"\b[a-z][a-z0-9-]*(?:cluster|cluster-\d+)[a-z0-9-]*\b", re.I)
STATUS_WORDS = {"success", "failed", "partial_failure", "running", "unknown"}
METRIC_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*%")


def _walk(obj: Any, key_hints: set[str], found: set[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in key_hints and isinstance(value, str) and value.strip():
                found.add(value.strip().lower())
            _walk(value, key_hints, found)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, key_hints, found)


def extract_entities_from_context(context: dict) -> set[str]:
    """Collect pipeline, cluster, and status tokens present in retrieved context."""
    entities: set[str] = set()
    key_hints = {
        "pipeline_name",
        "cluster_id",
        "cluster_name",
        "status",
        "root_cause",
        "instance_type",
        "recommended_type",
    }
    _walk(context, key_hints, entities)

    for key in ("summary",):
        summary = context.get(key)
        if isinstance(summary, dict):
            _walk(summary, key_hints, entities)

    return entities


def extract_pipeline_mentions(text: str, known_pipelines: set[str] | None = None) -> set[str]:
    """Find pipeline-like names mentioned in a response."""
    text_lower = text.lower()
    mentions: set[str] = set()

    if known_pipelines:
        for name in known_pipelines:
            display = name.replace("_", " ")
            if name in text_lower or display in text_lower:
                mentions.add(name)

    for match in PIPELINE_PATTERN.findall(text_lower):
        if known_pipelines is None or match in known_pipelines:
            mentions.add(match)

    return mentions


def extract_cluster_mentions(text: str, known_clusters: set[str] | None = None) -> set[str]:
    text_lower = text.lower()
    mentions: set[str] = set()

    if known_clusters:
        for cluster in known_clusters:
            if cluster in text_lower or cluster.replace("_", " ") in text_lower:
                mentions.add(cluster)

    for match in CLUSTER_PATTERN.findall(text_lower):
        normalized = match.lower().replace(" ", "_")
        if known_clusters is None or normalized in known_clusters or match.lower() in known_clusters:
            mentions.add(normalized)

    return mentions
