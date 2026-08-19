from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_pipeline_run_and_incident_listing(sample_csv):
    run_response = client.post("/pipeline/run", json={"csv_path": sample_csv, "clear_memory": True})
    assert run_response.status_code == 200
    body = run_response.json()
    assert body["incidents"] == 2

    incidents_response = client.get("/incidents")
    assert incidents_response.status_code == 200
    incidents = incidents_response.json()
    assert len(incidents) == 2

    incident_id = incidents[0]["incident_id"]
    detail_response = client.get(f"/incidents/{incident_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["incident_id"] == incident_id


def test_get_unknown_incident_returns_404():
    response = client.get("/incidents/DOES-NOT-EXIST")
    assert response.status_code == 404


def test_reports_summary_after_run(sample_csv):
    client.post("/pipeline/run", json={"csv_path": sample_csv, "clear_memory": True})
    response = client.get("/reports/summary")
    assert response.status_code == 200
    assert "executive_summary" in response.json()


def test_pipeline_status_tracks_stage_timings(sample_csv):
    """Module 4 workflow orchestration: every stage should be timed and
    reported as 'done' after a successful run, powering the dashboard's
    live workflow panel."""
    run_response = client.post("/pipeline/run", json={"csv_path": sample_csv, "clear_memory": True})
    assert run_response.status_code == 200
    assert "stage_timings" in run_response.json()

    status_response = client.get("/pipeline/status")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["pipeline_status"] == "idle"
    for stage in body["stages"]:
        assert body["stage_timings"][stage]["status"] == "done"
        assert body["stage_timings"][stage]["duration_seconds"] is not None


def test_metrics_endpoint_exposes_prometheus_format(sample_csv):
    """Module 5 monitoring: /metrics should be scrapeable Prometheus text
    exposition format and reflect at least one completed pipeline run."""
    client.post("/pipeline/run", json={"csv_path": sample_csv, "clear_memory": True})
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "pipeline_runs_total" in body
    assert "pipeline_stage_duration_seconds" in body
    assert "http_requests_total" in body


def test_upload_csv_and_run_against_it():
    """A user should be able to upload their own CSV and immediately run
    the pipeline against the returned path."""
    csv_bytes = (
        b"log_id,timestamp,source_ip,destination_ip,destination_port,protocol,"
        b"user,asset,asset_criticality,bytes_transferred,request_count,payload_snippet,status\n"
        b"1,2026-08-16T10:00:00Z,203.0.113.9,10.0.0.5,22,TCP,admin,bastion-01,"
        b'Critical,500,300,"999 failed logins",flagged\n'
    )
    upload_response = client.post(
        "/pipeline/upload-csv",
        files={"file": ("custom_logs.csv", csv_bytes, "text/csv")},
    )
    assert upload_response.status_code == 200
    body = upload_response.json()
    assert body["rows"] == 1
    assert "log_id" in body["columns"]
    assert body["csv_path"].startswith("data/uploads/")

    run_response = client.post(
        "/pipeline/run", json={"csv_path": body["csv_path"], "clear_memory": True}
    )
    assert run_response.status_code == 200
    assert run_response.json()["logs_processed"] == 1


def test_upload_csv_rejects_non_csv_file():
    response = client.post(
        "/pipeline/upload-csv",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_csv_rejects_missing_required_columns():
    response = client.post(
        "/pipeline/upload-csv",
        files={"file": ("bad.csv", b"a,b,c\n1,2,3\n", "text/csv")},
    )
    assert response.status_code == 400
    assert "missing required column" in response.json()["detail"]
