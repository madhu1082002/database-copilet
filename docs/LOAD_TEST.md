# Load / response-time evidence

Generated: 2026-09-11T14:35:28.078898+00:00

50 mixed queries (status, failure, optimization) via Flask test client, mock AI path, cache enabled after first cycle.

| Metric | Value |
|--------|-------|
| Queries | 50 |
| Min | 0.0275 s |
| Mean | 0.0547 s |
| p50 | 0.04 s |
| p95 | 0.1027 s |
| Max | 0.1936 s |
| All under 10s | Yes |

Locust (optional live HTTP): `pip install -r requirements-dev.txt` then `locust -f locustfile.py --headless -u 10 -r 2 -t 60s --host http://127.0.0.1:5000`.
