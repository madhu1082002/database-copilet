# DataOps Copilot (database-copilet)

**GenAI-Powered Data Ops Assistant** — based on the IMPACT pSIDDHI proposal (S3-D-08).

A conversational AI assistant that helps data engineers monitor pipelines, diagnose failures, and find cost optimization opportunities through natural language queries.

## Architecture

```
Web UI (Dashboard + Chat)  →  Flask REST API  →  Gemini AI + Mock Pipeline Data
```

| Layer | Technology |
|-------|-----------|
| Frontend | HTML/CSS/JS (web alternative to Power Apps) |
| Backend | Python Flask |
| AI Engine | Google Gemini 2.5 Flash (with rule-based mock fallback) |
| Data (Phase 1) | JSON mock datasets + SQLite query logging |
| Data (Phase 2) | Databricks Free Edition REST API (job runs, clusters) |

## Data Sources

| Mode | When | Source |
|------|------|--------|
| **Mock JSON** | Default | `backend/data/*.json` |
| **Databricks** | `USE_DATABRICKS=true` | Live job runs + cluster metrics |
| **SQLite** | Always | Query audit log (`dataops.db`) |

### Enable Databricks (Phase 2)

1. Create a [Databricks Free Edition](https://www.databricks.com/learn/free-edition) workspace
2. Generate a **Personal Access Token**: User Settings → Developer → Access tokens
3. Add to `.env`:

```env
USE_DATABRICKS=true
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your_token_here
```

4. Restart Flask: `py app.py`
5. Check connection: `GET http://localhost:5000/databricks/status`

If Databricks is unavailable, the app **automatically falls back** to mock JSON data.

## Features

1. **Pipeline Status** — "Did sales_etl run today?" / "Which pipelines failed?"
2. **Failure Diagnosis** — "Why did customer_ingestion fail?" with root cause and suggested actions
3. **Optimization** — "Can we reduce compute costs?" with cluster utilization and ₹ savings estimates

## Quick Start

```powershell
cd dataops-copilot
py -m pip install -r requirements.txt
cd backend
py app.py
```

> **Windows note:** If `python` is not found, use `py` instead (the Windows Python launcher).

Open **http://localhost:5000** in your browser.

## Enable Gemini AI

1. Get free key(s) from [Google AI Studio](https://aistudio.google.com/apikey)
2. Copy `.env.example` to `.env` and add your keys (comma-separated for automatic fallback):

```bash
GEMINI_API_KEYS=key1,key2,key3,key4,key5,key6
USE_MOCK_AI=false
```

If Key 1 hits quota or fails, the app automatically tries Key 2, then Key 3, and so on.

Without API keys, the app uses intelligent rule-based mock responses grounded in pipeline data.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/databricks/status` | Databricks connection status |
| GET | `/dashboard` | Pipeline dashboard summary |
| GET | `/pipeline-status` | Pipeline run data |
| GET | `/failure-diagnosis` | Failure logs and root causes |
| GET | `/optimization` | Cluster metrics and savings |
| POST | `/query` | Natural-language AI query |
| POST | `/feedback` | Thumbs up/down on responses |

## Run Tests

```bash
cd dataops-copilot
pip install -r requirements.txt
pytest tests/ -v
```

### AI-Assisted QA (pSIDDHI requirement)

Mock data validation + 50+ test query scenarios + hallucination measurement:

```powershell
# Validate 50+ mock pipeline scenarios
py scripts/validate_mock_data.py

# Regenerate 55+ test queries from mock data
py scripts/build_test_queries.py

# Run full AI QA report (offline, rule-based scoring)
py qa/run_ai_qa.py

# Optional: Gemini scoring + synthetic query generation
py qa/run_ai_qa.py --gemini-synthetic 10 --use-gemini-scoring
```

Reports are written to `reports/ai_qa_report.json`.

## Project Structure

```
dataops-copilot/
├── backend/
│   ├── app.py              # Flask API server
│   ├── config.py           # Configuration
│   ├── data/               # Mock pipeline JSON datasets
│   ├── models/database.py  # SQLite schema & logging
│   └── services/           # AI, intent, data retrieval
├── frontend/               # Dashboard + chat UI
├── data/                   # 50+ test query scenarios for AI QA
├── qa/                     # AI-assisted QA (hallucination, scoring, synthetic queries)
├── reports/                # Generated QA reports (gitignored)
├── scripts/                # Seed, validate, build test queries
├── tests/                  # Pytest test suite
└── requirements.txt
```

## Sample Queries

- "Did Sales ETL run today?"
- "Why did customer_ingestion fail?"
- "What caused yesterday's finance DAG failure?"
- "Can we reduce compute costs?"
- "Which pipelines failed in the last 24 hours?"
