import json

from config import settings
from pipeline import run_pipeline


def test_full_pipeline_run_produces_all_output_files(sample_csv):
    # Uses the process-wide shared-memory singleton (cleared at the start of
    # the run), since pipeline.run_pipeline() constructs its own agents
    # internally rather than accepting an injected memory instance.
    summary = run_pipeline(csv_path=sample_csv, clear_memory=True)

    assert summary["logs_processed"] == 3
    assert summary["suspicious_events"] == 2
    assert summary["incidents"] == 2
    assert summary["decisions"] == 2

    assert settings.detected_logs_csv.exists()
    assert settings.analyzed_logs_csv.exists()
    assert settings.coordinated_tasks_csv.exists()
    assert settings.decision_output_csv.exists()
    assert settings.response_output_csv.exists()
    assert settings.alert_output_csv.exists()
    assert settings.final_report_csv.exists()
    assert settings.incident_report_json.exists()
    assert settings.incident_report_md.exists()

    report = json.loads(settings.incident_report_json.read_text(encoding="utf-8"))
    assert report["incident_count"] == 2
    assert "executive_summary" in report
