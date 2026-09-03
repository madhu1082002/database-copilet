# User guide

## Start Copilot

```powershell
cd dataops-copilot
py -m pip install -r requirements.txt
copy .env.example .env
cd backend
py app.py
```

Open http://localhost:5000

Without Gemini keys the assistant uses grounded rule-based answers. Set `USE_MOCK_AI=false` and `GEMINI_API_KEYS=...` to use Gemini 2.5 Flash.

## Start the Pipeline Data Portal (optional)

```powershell
cd pipeline-portal
py -m pip install -r requirements.txt
cd backend
py app.py
```

Open http://localhost:5001 — add/edit/delete pipeline runs, failures, and cluster metrics. Refresh Copilot to see the change when Databricks is enabled.

## What to ask

- **Pipeline status:** "Did Sales ETL run today?" / "Which pipelines failed in the last 24 hours?"
- **Failure diagnosis:** "Why did customer_ingestion fail?"
- **Optimization:** "Can we reduce compute costs?"

Use the category dropdown to force an intent, or leave it on Auto. Click a pipeline row to ask about that run. Use Helpful / Not helpful so the answer is stored in the SQLite audit log.

## Data sources

The header badge shows **Mock JSON**, **Databricks Live**, or **Databricks Tables**. Mock JSON is the default and is enough for the demo if Databricks credentials are not configured.
