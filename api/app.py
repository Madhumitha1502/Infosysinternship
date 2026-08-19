"""
api/app.py
===========
FastAPI REST API for the AI Cyber Attack Response Coordinator.

Endpoints:
    GET  /health                       - liveness/readiness probe
    POST /pipeline/upload-csv          - upload a custom network-log CSV
    POST /pipeline/run                 - trigger a full pipeline run
    GET  /pipeline/status              - live per-stage workflow status
    GET  /incidents                    - list all incidents in shared memory
    GET  /incidents/{incident_id}      - get a single incident's full detail
    POST /incidents/{incident_id}/approve - approve a pending disruptive response action
    GET  /reports/summary              - latest report summary (executive summary + counts)
    GET  /events                       - full audit-log event stream
    GET  /metrics                      - Prometheus-compatible plaintext metrics

Interactive Swagger docs are available at /docs (ReDoc at /redoc), generated
automatically by FastAPI from the type-annotated route signatures below.
"""

from __future__ import annotations

import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.alert_agent import AlertAgent
from agents.response_agent import ResponseAgent
from config import settings
from logging_setup import get_logger
from memory.shared_memory import shared_memory
from models import CoordinatedIncident, Decision
from pipeline import PIPELINE_STAGES, run_pipeline

logger = get_logger("api")

#: Where uploaded CSVs land. Kept separate from data/network_logs.csv (the
#: bundled sample) so an upload never clobbers the sample dataset.
UPLOADS_DIR = settings.data_dir / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

#: Columns the detection agent's NetworkLogEntry model requires -- anything
#: else in models.NetworkLogEntry is optional. Validated at upload time so
#: a bad file fails fast with a clear message instead of a confusing
#: mid-pipeline error.
REQUIRED_CSV_COLUMNS = ["log_id", "timestamp", "source_ip", "destination_ip"]
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB is generous for a CSV of log rows

FRONTEND_DIR = settings.base_dir / "frontend"

# ------------------------------------------------------------------
# Lightweight in-process monitoring counters (Module 5: "implement
# monitoring, logging, scalability, and performance optimization").
# These are process-local by design -- no external dependency (e.g. Redis)
# is required to demo/deploy the monitoring surface, and they reset on
# restart, which is acceptable for a single-instance/dev deployment. For a
# horizontally-scaled deployment, swap this for a shared backend (Redis,
# Prometheus pushgateway, etc.) without changing the /metrics contract.
# ------------------------------------------------------------------
_METRICS: dict[str, Any] = {
    "requests_total": defaultdict(int),  # keyed by "METHOD path"
    "request_duration_seconds_sum": defaultdict(float),
    "pipeline_runs_total": 0,
    "pipeline_run_errors_total": 0,
    "process_started_at": time.time(),
}

app = FastAPI(
    title=settings.app_name,
    description=(
        "Enterprise multi-agent AI system for detecting, analyzing, "
        "prioritizing, responding to, and reporting on cyber attacks. "
        "A static SOC dashboard is served at `/` — the JSON API below "
        "powers it and can also be used standalone."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _metrics_middleware(request: Request, call_next):
    """Record request counts + latency for every call, for GET /metrics."""
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - t0
    route = request.scope.get("route")
    path_template = route.path if route is not None else request.url.path
    key = f"{request.method} {path_template}"
    _METRICS["requests_total"][key] += 1
    _METRICS["request_duration_seconds_sum"][key] += elapsed
    response.headers["X-Response-Time-ms"] = f"{elapsed * 1000:.2f}"
    return response

# ------------------------------------------------------------------
# Frontend: static dashboard (vanilla HTML/CSS/JS, no build step)
# ------------------------------------------------------------------
if (FRONTEND_DIR / "static").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "static"), name="assets")


@app.get("/", include_in_schema=False)
def serve_dashboard() -> FileResponse:
    """Serve the SOC dashboard single-page app."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard not built. See /docs for the JSON API.")
    return FileResponse(index_path)


class PipelineRunRequest(BaseModel):
    csv_path: Optional[str] = None
    clear_memory: bool = True


class PipelineRunResponse(BaseModel):
    elapsed_seconds: float
    logs_processed: int
    suspicious_events: int
    incidents: int
    decisions: int
    responses: int
    alerts: int
    executive_summary: str
    severity_breakdown: dict[str, int]
    incident_count: int
    final_report_csv: str
    incident_report_json: str
    incident_report_md: str
    stage_timings: dict[str, Any] = {}


class CsvUploadResponse(BaseModel):
    csv_path: str
    filename: str
    rows: int
    columns: list[str]


class ApprovalResponse(BaseModel):
    incident_id: str
    action: str
    status: str
    success: bool


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    """Liveness/readiness probe."""
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@app.post("/pipeline/upload-csv", response_model=CsvUploadResponse, tags=["Pipeline"])
async def upload_csv(file: UploadFile = File(...)) -> Any:
    """
    Upload a custom network-log CSV to feed into the pipeline instead of the
    bundled sample dataset. Returns a `csv_path` you then pass to
    `POST /pipeline/run` (the dashboard's "Upload CSV" button does both
    steps for you automatically).

    Validates: file extension, size, and that the required columns
    (log_id, timestamp, source_ip, destination_ip) are present -- so a
    malformed file fails here with a clear message rather than partway
    through the pipeline.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)}MB).")

    try:
        df = pd.read_csv(pd.io.common.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}") from exc

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV has no data rows.")

    missing = [col for col in REQUIRED_CSV_COLUMNS if col not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required column(s): {', '.join(missing)}. "
                   f"Required: {', '.join(REQUIRED_CSV_COLUMNS)}.",
        )

    # Safe, collision-proof filename: strip path separators, prefix with a
    # timestamp + short uuid so concurrent uploads (or repeated uploads of
    # "network_logs.csv") never overwrite each other or the bundled sample.
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(file.filename).stem)[:60] or "upload"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest_name = f"{stamp}_{uuid.uuid4().hex[:8]}_{safe_stem}.csv"
    dest_path = UPLOADS_DIR / dest_name
    df.to_csv(dest_path, index=False)

    logger.info("Uploaded CSV saved to %s (%d rows, %d columns)", dest_path, len(df), len(df.columns))
    shared_memory.log_event("api", "csv_uploaded", {
        "original_filename": file.filename, "saved_as": str(dest_path), "rows": len(df),
    })

    return CsvUploadResponse(
        csv_path=str(dest_path.relative_to(settings.base_dir)),
        filename=file.filename,
        rows=len(df),
        columns=list(df.columns),
    )


@app.post("/pipeline/run", response_model=PipelineRunResponse, tags=["Pipeline"])
def trigger_pipeline_run(request: PipelineRunRequest) -> Any:
    """Run the full detection -> analysis -> coordination -> decision -> response -> alert -> report pipeline."""
    try:
        summary = run_pipeline(csv_path=request.csv_path, clear_memory=request.clear_memory)
        _METRICS["pipeline_runs_total"] += 1
        return summary
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        _METRICS["pipeline_run_errors_total"] += 1
        logger.exception("Pipeline run failed via API: %s", exc)
        raise HTTPException(status_code=500, detail="Pipeline run failed") from exc


@app.get("/pipeline/status", tags=["Pipeline"])
def get_pipeline_status() -> dict[str, Any]:
    """
    Live workflow status: per-stage state (pending/running/done/error) and
    duration for the most recent (or currently in-flight) pipeline run.
    Powers the dashboard's workflow orchestration visualization.
    """
    stage_timings = shared_memory.get_state("stage_timings", {})
    ordered = {stage: stage_timings.get(stage, {"status": "pending", "duration_seconds": None}) for stage in PIPELINE_STAGES}
    return {
        "pipeline_status": shared_memory.get_state("pipeline_status", "idle"),
        "stages": PIPELINE_STAGES,
        "stage_timings": ordered,
        "last_run_summary": shared_memory.get_state("last_run_summary", None),
    }


@app.get("/incidents", tags=["Incidents"])
def list_incidents() -> list[dict[str, Any]]:
    """List all incidents currently tracked in shared memory, most recently updated first."""
    return shared_memory.all_incidents()


@app.get("/incidents/{incident_id}", tags=["Incidents"])
def get_incident(incident_id: str) -> dict[str, Any]:
    """Get full detail for a single incident."""
    incident = shared_memory.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return incident


@app.post("/incidents/{incident_id}/approve", response_model=ApprovalResponse, tags=["Incidents"])
def approve_incident_action(incident_id: str) -> Any:
    """
    Approve and execute a response action that was deferred pending human
    approval (e.g. disable_user, isolate_device, quarantine_device on a
    non-Critical incident).
    """
    incident_record = shared_memory.get_incident(incident_id)
    if incident_record is None:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    decisions = shared_memory.get_state("decisions", [])
    decision_data = next((d for d in decisions if d["incident_id"] == incident_id), None)
    if decision_data is None:
        raise HTTPException(status_code=404, detail=f"No decision found for incident '{incident_id}'")

    decision = Decision(**decision_data)
    if not decision.requires_human_approval:
        raise HTTPException(status_code=400, detail="This incident's action does not require approval")

    incident = CoordinatedIncident(**incident_record["data"])
    approved_decision = decision.model_copy(update={"requires_human_approval": False})

    response_agent = ResponseAgent()
    result = response_agent._execute_one(incident, approved_decision)  # noqa: SLF001 - intentional reuse

    # Persist updated response result back into shared memory
    all_results = shared_memory.get_state("response_results", [])
    all_results = [r for r in all_results if r["incident_id"] != incident_id]
    all_results.append(result.model_dump())
    shared_memory.set_state("response_results", all_results)

    # Fire an alert reflecting the newly-approved action
    alert_agent = AlertAgent()
    alert_agent.run([incident], [approved_decision], [result])

    return ApprovalResponse(
        incident_id=incident_id, action=result.action.value, status=result.status, success=result.success
    )


@app.get("/reports/summary", tags=["Reports"])
def get_report_summary() -> dict[str, Any]:
    """Return the executive summary and severity breakdown from the most recent report."""
    import json

    if not settings.incident_report_json.exists():
        raise HTTPException(status_code=404, detail="No report has been generated yet. Run the pipeline first.")
    data = json.loads(settings.incident_report_json.read_text(encoding="utf-8"))
    return {
        "generated_at": data.get("generated_at"),
        "executive_summary": data.get("executive_summary"),
        "severity_breakdown": data.get("severity_breakdown"),
        "incident_count": data.get("incident_count"),
    }


@app.get("/events", tags=["Audit"])
def list_events(agent: Optional[str] = None) -> list[dict[str, Any]]:
    """Return the full audit-log event stream, optionally filtered by agent name."""
    return shared_memory.get_events(agent=agent)


@app.get("/metrics", tags=["System"], response_class=PlainTextResponse)
def metrics() -> str:
    """
    Prometheus-compatible plaintext metrics endpoint (Module 5: monitoring &
    performance optimization). Scrape this with Prometheus, or curl it
    directly for a quick operational snapshot. No external dependency
    (e.g. prometheus_client) is required -- the exposition format is just
    text, so it's produced here manually to keep the deployment footprint
    minimal.
    """
    lines: list[str] = []
    uptime = time.time() - _METRICS["process_started_at"]

    lines.append("# HELP app_uptime_seconds Time since the API process started")
    lines.append("# TYPE app_uptime_seconds gauge")
    lines.append(f"app_uptime_seconds {uptime:.2f}")

    lines.append("# HELP pipeline_runs_total Total number of pipeline runs triggered via the API")
    lines.append("# TYPE pipeline_runs_total counter")
    lines.append(f"pipeline_runs_total {_METRICS['pipeline_runs_total']}")

    lines.append("# HELP pipeline_run_errors_total Total number of pipeline runs that raised an error")
    lines.append("# TYPE pipeline_run_errors_total counter")
    lines.append(f"pipeline_run_errors_total {_METRICS['pipeline_run_errors_total']}")

    lines.append("# HELP incidents_tracked_total Number of incidents currently tracked in shared memory")
    lines.append("# TYPE incidents_tracked_total gauge")
    lines.append(f"incidents_tracked_total {len(shared_memory.all_incidents())}")

    lines.append("# HELP http_requests_total Total HTTP requests received, by method+route")
    lines.append("# TYPE http_requests_total counter")
    for key, count in _METRICS["requests_total"].items():
        method, route = key.split(" ", 1)
        lines.append(f'http_requests_total{{method="{method}",route="{route}"}} {count}')

    lines.append("# HELP http_request_duration_seconds_sum Cumulative request latency, by method+route")
    lines.append("# TYPE http_request_duration_seconds_sum counter")
    for key, total_seconds in _METRICS["request_duration_seconds_sum"].items():
        method, route = key.split(" ", 1)
        lines.append(f'http_request_duration_seconds_sum{{method="{method}",route="{route}"}} {total_seconds:.6f}')

    stage_timings = shared_memory.get_state("stage_timings", {})
    lines.append("# HELP pipeline_stage_duration_seconds Duration of the most recent run of each pipeline stage")
    lines.append("# TYPE pipeline_stage_duration_seconds gauge")
    for stage, info in stage_timings.items():
        duration = info.get("duration_seconds")
        if duration is not None:
            lines.append(f'pipeline_stage_duration_seconds{{stage="{stage}"}} {duration}')

    return "\n".join(lines) + "\n"
