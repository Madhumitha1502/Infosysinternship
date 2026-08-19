"""
pipeline.py
============
Orchestrates the full multi-agent workflow end-to-end:

    CSV logs -> Detection -> Analysis -> Coordination -> Decision Engine
             -> Response -> Alerting -> Reporting

Besides the final report artifacts, this module is responsible for writing
every intermediate CSV snapshot requested by the project spec:
    detected_logs.csv, analyzed_logs.csv, coordinated_tasks.csv,
    decision_output.csv, response_output.csv, alert_output.csv

so that each stage of the pipeline is independently auditable.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator

import pandas as pd

from agents.alert_agent import AlertAgent
from agents.analysis_agent import AnalysisAgent
from agents.coordination_agent import CoordinationAgent
from agents.decision_engine import DecisionEngine
from agents.detection_agent import DetectionAgent
from agents.report_agent import ReportAgent
from agents.response_agent import ResponseAgent
from config import settings
from logging_setup import get_logger
from memory.shared_memory import shared_memory

logger = get_logger("pipeline")

#: Canonical ordered list of workflow stages, used by both the orchestrator
#: (below) and the dashboard's live workflow visualization (via
#: GET /pipeline/status) so the UI can render node-by-node progress without
#: guessing at stage names.
PIPELINE_STAGES: list[str] = [
    "detection",
    "analysis",
    "coordination",
    "decision",
    "response",
    "alert",
    "report",
]


def _write_csv(records: list[dict[str, Any]], path) -> None:
    pd.DataFrame(records).to_csv(path, index=False)
    logger.info("Wrote %d rows to %s", len(records), path)


@contextmanager
def _timed_stage(stage_timings: dict[str, dict[str, Any]], stage: str) -> Iterator[None]:
    """Track wall-clock timing + running/ok/error status for one pipeline stage.

    Every transition is (a) written into `stage_timings` (persisted to shared
    memory immediately, so the API can expose live progress mid-run) and
    (b) logged as an audit event, which is how the dashboard's workflow
    panel animates node-by-node without any extra plumbing.
    """
    stage_timings[stage] = {"status": "running", "started_at": time.time(), "duration_seconds": None}
    shared_memory.set_state("stage_timings", stage_timings)
    shared_memory.log_event("pipeline", "stage_started", {"stage": stage})
    t0 = time.perf_counter()
    try:
        yield
    except Exception as exc:  # noqa: BLE001
        stage_timings[stage]["status"] = "error"
        stage_timings[stage]["duration_seconds"] = round(time.perf_counter() - t0, 4)
        shared_memory.set_state("stage_timings", stage_timings)
        shared_memory.log_event("pipeline", "stage_failed", {"stage": stage, "error": str(exc)})
        raise
    else:
        stage_timings[stage]["status"] = "done"
        stage_timings[stage]["duration_seconds"] = round(time.perf_counter() - t0, 4)
        shared_memory.set_state("stage_timings", stage_timings)
        shared_memory.log_event(
            "pipeline", "stage_completed",
            {"stage": stage, "duration_seconds": stage_timings[stage]["duration_seconds"]},
        )


def run_pipeline(csv_path: str | None = None, clear_memory: bool = True) -> dict[str, Any]:
    """Run the full incident-response pipeline once and return a summary dict."""
    start = time.perf_counter()
    logger.info("=== Starting AI Cyber Attack Response pipeline run ===")

    if clear_memory:
        shared_memory.clear()

    stage_timings: dict[str, dict[str, Any]] = {
        stage: {"status": "pending", "started_at": None, "duration_seconds": None}
        for stage in PIPELINE_STAGES
    }
    shared_memory.set_state("stage_timings", stage_timings)
    shared_memory.set_state("pipeline_status", "running")

    try:
        # Step 1 & 2: load logs + detect
        with _timed_stage(stage_timings, "detection"):
            detection_agent = DetectionAgent()
            detected_events = detection_agent.run(csv_path)
            _write_csv([e.model_dump() for e in detected_events], settings.detected_logs_csv)

        # Step 3: analyze
        with _timed_stage(stage_timings, "analysis"):
            analysis_agent = AnalysisAgent()
            analyzed_events = analysis_agent.run(detected_events)
            _write_csv([e.model_dump() for e in analyzed_events], settings.analyzed_logs_csv)

        # Step 4: coordinate / prioritize
        with _timed_stage(stage_timings, "coordination"):
            coordination_agent = CoordinationAgent()
            incidents = coordination_agent.run(analyzed_events)
            _write_csv([i.model_dump() for i in incidents], settings.coordinated_tasks_csv)

        # Step 5: decide
        with _timed_stage(stage_timings, "decision"):
            decision_engine = DecisionEngine()
            decisions = decision_engine.run(incidents)
            _write_csv([d.model_dump() for d in decisions], settings.decision_output_csv)

        # Step 6: respond
        with _timed_stage(stage_timings, "response"):
            response_agent = ResponseAgent()
            response_results = response_agent.run(incidents, decisions)
            _write_csv([r.model_dump() for r in response_results], settings.response_output_csv)

        # Merge decision + response outcomes back into each incident record so
        # the dashboard's incident table (GET /incidents) can show the actual
        # decided action and response status per-row, not just in the
        # aggregate run summary. Without this, /incidents only ever reflects
        # the coordination-stage snapshot (pre-decision), which is why the
        # UI would otherwise show "queued"/"-" for every row regardless of
        # what actually happened.
        decisions_by_id = {d.incident_id: d for d in decisions}
        response_by_id = {r.incident_id: r for r in response_results}
        for incident in incidents:
            decision = decisions_by_id.get(incident.incident_id)
            result = response_by_id.get(incident.incident_id)
            enriched = incident.model_dump()
            if decision is not None:
                enriched["decided_action"] = decision.action.value
                enriched["decision_justification"] = decision.justification
                enriched["requires_human_approval"] = decision.requires_human_approval
            if result is not None:
                enriched["response_status"] = result.status
                enriched["response_success"] = result.success
                enriched["runbook_note"] = result.runbook_note
            shared_memory.upsert_incident(incident.incident_id, enriched)

        # Step 7: alert
        with _timed_stage(stage_timings, "alert"):
            alert_agent = AlertAgent()
            alert_records = alert_agent.run(incidents, decisions, response_results)
            _write_csv([a.model_dump() for a in alert_records], settings.alert_output_csv)

        # Step 8: report
        with _timed_stage(stage_timings, "report"):
            report_agent = ReportAgent()
            report_summary = report_agent.run(incidents, decisions, response_results, alert_records)
    except Exception:
        shared_memory.set_state("pipeline_status", "error")
        raise

    elapsed = time.perf_counter() - start
    shared_memory.set_state("pipeline_status", "idle")
    shared_memory.set_state("last_run_summary", {
        "elapsed_seconds": round(elapsed, 2),
        "logs_processed": len(detected_events),
        "incidents": len(incidents),
    })
    logger.info("=== Pipeline run complete in %.2fs ===", elapsed)

    return {
        "elapsed_seconds": round(elapsed, 2),
        "logs_processed": len(detected_events),
        "suspicious_events": len(analyzed_events),
        "incidents": len(incidents),
        "decisions": len(decisions),
        "responses": len(response_results),
        "alerts": len(alert_records),
        "stage_timings": stage_timings,
        **report_summary,
    }
