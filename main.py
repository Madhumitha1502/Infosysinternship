"""
main.py
========
CLI entry point for the AI Cyber Attack Response Coordinator.

Usage:
    python main.py                       # run the pipeline against the default dataset
    python main.py --csv path/to/logs.csv  # run against a custom dataset
    python main.py --no-clear             # keep prior shared-memory state (resume/audit mode)
"""

from __future__ import annotations

import argparse
import json
import sys

from logging_setup import get_logger
from pipeline import run_pipeline

logger = get_logger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Multi-Agent Cyber Attack Response Coordinator"
    )
    parser.add_argument(
        "--csv", dest="csv_path", default=None,
        help="Path to the network logs CSV file (defaults to data/network_logs.csv)",
    )
    parser.add_argument(
        "--no-clear", dest="clear_memory", action="store_false",
        help="Do not clear shared memory before this run",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = run_pipeline(csv_path=args.csv_path, clear_memory=args.clear_memory)
    except FileNotFoundError as exc:
        logger.error("Pipeline aborted: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline run failed unexpectedly: %s", exc)
        return 1

    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
