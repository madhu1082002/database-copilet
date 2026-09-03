"""Locust load test for DataOps Copilot.

Run against a live server:

    locust -f locustfile.py --headless -u 10 -r 2 -t 60s --host http://127.0.0.1:5000
"""

from locust import HttpUser, between, task


class CopilotUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(3)
    def dashboard(self):
        self.client.get("/dashboard")

    @task(2)
    def pipeline_status(self):
        self.client.get("/pipeline-status")

    @task(2)
    def failure_diagnosis(self):
        self.client.get("/failure-diagnosis")

    @task(2)
    def optimization(self):
        self.client.get("/optimization")

    @task(5)
    def query_status(self):
        self.client.post("/query", json={"query": "Did sales_etl run today?"})

    @task(4)
    def query_failure(self):
        self.client.post("/query", json={"query": "Why did customer_ingestion fail?"})

    @task(3)
    def query_optimization(self):
        self.client.post("/query", json={"query": "Can we reduce compute costs?"})
