# QA report — measured 03-Sep-2026

## Pytest coverage (pytest-cov)

Command:

```
pytest tests/ -v --cov=app --cov=config --cov=models --cov=services --cov=qa --cov-report=term-missing --cov-fail-under=80
```

Result: **75 tests passed**, **total coverage 83%** (gate ≥80% met).

Portal: **20 tests passed**.

GitHub Actions workflow: `.github/workflows/ci.yml` (runs after you push).

## Intent / hallucination

Mock AI path (`py qa/run_ai_qa.py`), 03-Sep-2026:

- Evaluated: 54
- Intent accuracy: **100%**
- Hallucination rate: **0%**
- Average overall score: **93.17**

Live Gemini 2.5 Flash: free-tier quota was exhausted (HTTP 429). The app fell back to the rule-based engine; a sample of 8 queries still scored intent 100% / hallucination 0%. For the live demo, either wait for quota reset or run with `USE_MOCK_AI=true`.

## Response time

See [LOAD_TEST.md](LOAD_TEST.md). 50 queries, p95 **0.009 s**, all under 10 s.

## Postman

Import `postman/DataOps_Copilot.postman_collection.json`.
