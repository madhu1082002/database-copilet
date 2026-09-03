# Load / response-time evidence

Generated: 2026-09-03T16:34:07.597901+00:00

50 mixed queries (status, failure, optimization) via Flask test client, mock AI path, cache enabled after first cycle.

| Metric | Value |
|--------|-------|
| Queries | 50 |
| Min | 0.0042 s |
| Mean | 0.0059 s |
| p50 | 0.0051 s |
| p95 | 0.0093 s |
| Max | 0.0116 s |
| All under 10s | Yes |

Locust (optional live HTTP): `pip install -r requirements-dev.txt` then `locust -f locustfile.py --headless -u 10 -r 2 -t 60s --host http://127.0.0.1:5000`.
