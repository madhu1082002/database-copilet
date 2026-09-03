# Demo script (Week 17)

Record a 4–6 minute video covering this path.

1. **Dashboard (30s)** — Open http://localhost:5000. Point at total / success / failed counts and Potential Savings. Show the data-source badge.
2. **Pipeline status (45s)** — Ask: "Did sales_etl run today?" Show the intent tag, confidence, and source names.
3. **Failure diagnosis (60s)** — Ask: "Why did customer_ingestion fail?" Read root cause and suggested actions.
4. **Optimization (45s)** — Ask: "Can we reduce compute costs?" Point at ₹ savings that come from stored cluster metrics.
5. **Feedback (20s)** — Click Helpful. Mention that SQLite now stores thumbs up/down against `query_id`.
6. **Portal write-through (60s, if Databricks is live)** — On http://localhost:5001 change a pipeline status, refresh Copilot, show the dashboard update.
7. **QA evidence (30s)** — Show GitHub Actions green run, coverage ≥80%, and `reports/ai_qa_report.json` (hallucination &lt;10%).

If Databricks is not available, skip step 6 and state that mock JSON is the approved Phase 1 fallback.
