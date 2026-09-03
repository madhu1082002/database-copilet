"""Build source-data references from retrieved RAG context."""

from __future__ import annotations


def extract_sources(intent: str, context: dict) -> list[dict]:
    sources: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, name: str | None, extra: dict | None = None) -> None:
        if not name:
            return
        key = (kind, name)
        if key in seen:
            return
        seen.add(key)
        item = {"type": kind, "name": name}
        if extra:
            item.update({k: v for k, v in extra.items() if v is not None})
        sources.append(item)

    if "summary" in context:
        add("dashboard", "pipeline_dashboard")

    for pipeline in context.get("pipelines") or context.get("pipeline_runs") or []:
        add("pipeline", pipeline.get("pipeline_name"), {"status": pipeline.get("status")})

    for failure in context.get("failures") or context.get("recent_failures") or []:
        add("failure", failure.get("pipeline_name"), {"root_cause": failure.get("root_cause")})

    for cluster in context.get("optimization_opportunities") or []:
        add(
            "cluster",
            cluster.get("cluster_name") or cluster.get("cluster_id"),
            {"estimated_savings_inr": cluster.get("estimated_savings_inr")},
        )

    if intent == "optimization" and not context.get("optimization_opportunities"):
        for cluster in context.get("clusters") or []:
            add("cluster", cluster.get("cluster_name") or cluster.get("cluster_id"))

    return sources[:12]
