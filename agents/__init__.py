"""
agents package
===============
Each module implements one specialized agent in the multi-agent pipeline:

    detection_agent    -> flags suspicious log entries
    analysis_agent      -> classifies threat type / severity / MITRE mapping
    coordination_agent  -> prioritizes incidents into a work queue
    decision_engine      -> chooses the best automated response action
    response_agent      -> executes response actions via tools/
    alert_agent          -> sends email / Slack / JSON alerts
    report_agent          -> produces CSV / JSON / Markdown / executive reports

All agents share a common `BaseAgent` (see `agents.base_agent`) for logging,
shared-memory access, and LLM-with-heuristic-fallback helpers.
"""
