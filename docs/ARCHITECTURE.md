# Architecture

```
Engineer (browser)
        │
        ▼
HTML/CSS/JS chat + dashboard     Pipeline Data Portal
        │  :5000                          │ :5001
        ▼                                 ▼
Flask REST API  ──────────────────►  Databricks Delta tables
        │                            (pipeline_runs, failure_logs,
        │                             cluster_metrics)
        ├── Intent classifier
        ├── JSON mock data (Phase 1 / fallback)
        ├── SQLite query_log (audit + thumbs feedback)
        ├── Response cache (repeated queries)
        └── Gemini 2.5 Flash (RAG-style context injection)
                └── rule-based mock fallback
```

## Layers

1. **UI** — conversational chat (category selector, history, thumbs up/down, confidence, sources) plus a live pipeline dashboard. **Power Apps is not used for the final demo.** The approved Canvas App was replaced by this HTML/CSS/JS web UI (disclosed deviation). `power-apps/openapi.json` is retained only as optional connector documentation, not as a required deliverable.
2. **API** — Flask endpoints for health, dashboard, pipeline status, failure diagnosis, optimization, `/query`, and `/feedback`.
3. **Data** — mock JSON by default; Databricks tables when `USE_DATABRICKS=true`. The Portal writes the same tables Copilot reads.
4. **GenAI** — Gemini 2.5 Flash with retrieved pipeline/failure/cluster JSON injected into every prompt. Offline fallback is the rule-based mock engine. Gemini calls time out after `GEMINI_TIMEOUT_SECONDS` (default 8s).

## Query flow

1. Engineer types a natural-language question.
2. Intent classifier scores Pipeline Status / Failure Diagnosis / Optimization (or uses the category hint).
3. Data service retrieves matching records (JSON or Databricks).
4. Prompt builder injects that context (RAG-style grounding).
5. Cache returns a previous answer when the same query+intent+source was seen within `CACHE_TTL_SECONDS`.
6. Otherwise Gemini (or the mock engine) generates the answer.
7. SQLite stores query, intent, response, timestamp; the API returns `query_id`.
8. Thumbs up/down posts to `/feedback` and updates that row.

Quantified ₹ savings come only from stored `cluster_metrics.estimated_savings_inr` (mock JSON or Delta table). The Databricks Clusters REST API does not invent CPU or savings.
