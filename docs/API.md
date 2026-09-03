# API reference

Base URL: `http://127.0.0.1:5000`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Chat + dashboard UI |
| GET | `/health` | Service health and data source |
| GET | `/databricks/status` | Databricks connection mode |
| GET | `/dashboard` | KPI summary + pipeline list |
| GET | `/pipeline-status` | Optional `?pipeline=` filter |
| GET | `/failure-diagnosis` | Optional `?pipeline=` filter |
| GET | `/optimization` | Clusters + stored ₹ savings |
| POST | `/query` | Natural-language query |
| POST | `/feedback` | Thumbs up/down for a `query_id` |
| GET | `/qa/anomaly` | No-data rate on recent answers |

## POST /query

```json
{ "query": "Why did customer_ingestion fail?", "category": "failure_diagnosis" }
```

`category` is optional (`pipeline_status` | `failure_diagnosis` | `optimization`).

Success:

```json
{
  "query": "Why did customer_ingestion fail?",
  "query_id": 42,
  "intent": "failure_diagnosis",
  "pipeline": "customer_ingestion",
  "response": "...",
  "category": "failure_diagnosis",
  "confidence": 1.0,
  "sources": [{ "type": "failure", "name": "customer_ingestion" }],
  "cached": false,
  "anomaly": { "anomaly": false, "no_data_rate": 0.0, "sample_size": 12 }
}
```

Empty query returns **400**.

## POST /feedback

```json
{ "query_id": 42, "feedback": "up" }
```

Unknown `query_id` returns **404**.

A Postman collection is in `postman/DataOps_Copilot.postman_collection.json`. The OpenAPI spec for a Power Apps connector is in `power-apps/openapi.json`.
