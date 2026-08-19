"""
tests/performance/locustfile.py
================================
Optional Locust load-test profile (Module 5: performance testing).

`scripts/perf_test.py` at the repo root is the zero-dependency default; use
this file instead if `locust` is already available and you want a ramping
load profile + the Locust web UI.

Install:
    pip install locust

Run (headless, 20 users, ramp 5/s, 2 minutes):
    locust -f tests/performance/locustfile.py --host http://localhost:8000 \
        --headless -u 20 -r 5 -t 2m

Run with the web UI instead:
    locust -f tests/performance/locustfile.py --host http://localhost:8000
    # then open http://localhost:8089
"""

from __future__ import annotations

from locust import HttpUser, between, task


class SocDashboardUser(HttpUser):
    """Simulates a SOC analyst's browser polling the dashboard + API."""

    wait_time = between(1, 3)

    @task(5)
    def health(self) -> None:
        self.client.get("/health")

    @task(4)
    def list_incidents(self) -> None:
        self.client.get("/incidents")

    @task(3)
    def pipeline_status(self) -> None:
        self.client.get("/pipeline/status")

    @task(3)
    def report_summary(self) -> None:
        self.client.get("/reports/summary")

    @task(2)
    def events(self) -> None:
        self.client.get("/events")

    @task(1)
    def run_pipeline(self) -> None:
        # Heaviest endpoint -- intentionally low weight so it doesn't
        # dominate the load profile the way a real "run" button wouldn't.
        self.client.post("/pipeline/run", json={"clear_memory": True})
