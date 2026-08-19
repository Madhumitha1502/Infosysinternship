# Cyber Incident Response Report

_Generated: 2026-08-17T13:36:16.977169+00:00_

## Executive Summary

During this run, 5 incidents were identified and triaged. Severity breakdown — Critical: 2, High: 2, Medium: 0, Low: 1. 5 automated response action(s) were taken by the system. 0 incident(s) require human approval before disruptive containment actions are executed. Overall risk posture for this run is elevated.

## Severity Breakdown

| Severity | Count |
|---|---|
| Low | 1 |
| Medium | 0 |
| High | 2 |
| Critical | 2 |

## Incident Detail

| Rank | Incident ID | Threat Type | Severity | Risk Score | Asset | Action | Status |
|---|---|---|---|---|---|---|---|
| 1 | INC-LOG-105-967966 | Ransomware | Critical | 94.5 | file-server-01 | quarantine_device | simulated |
| 2 | INC-LOG-103-9FCD4B | DDoS | Critical | 87.5 | firewall-01 | rate_limit | simulated |
| 3 | INC-LOG-101-F105B9 | Brute Force | High | 81.5 | bastion-01 | block_ip | simulated |
| 4 | INC-LOG-102-432B2E | SQL Injection | High | 70.25 | web-01 | generate_firewall_rule | simulated |
| 5 | INC-LOG-104-2A1702 | Port Scanning | Low | 47.25 | workstation-14 | block_ip | simulated |