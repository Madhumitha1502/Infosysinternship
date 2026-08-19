"""
scripts/perf_test.py
=====================
Lightweight performance / load test for Milestone 4 ("Conduct performance
testing and optimization"). Intentionally dependency-free (uses only the
Python standard library) so it runs anywhere the API runs -- no `locust` or
`pip install` required in CI or on a fresh deployment.

It hammers a running instance of the API with concurrent requests against a
mix of read endpoints and full pipeline runs, then reports latency
percentiles and throughput per endpoint.

Usage:
    # 1. Start the API in one terminal:
    uvicorn api.app:app --port 8000

    # 2. Run the load test in another terminal:
    python scripts/perf_test.py --base-url http://localhost:8000 \
        --concurrency 10 --requests 100

A companion Locust file (tests/performance/locustfile.py) is also provided
for teams that already have `locust` installed and want a web UI / ramping
load profile instead.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field


@dataclass
class EndpointSpec:
    name: str
    method: str
    path: str
    body: dict | None = None


@dataclass
class Result:
    ok: bool
    status: int
    latency_seconds: float


@dataclass
class Aggregate:
    latencies: list[float] = field(default_factory=list)
    errors: int = 0
    total: int = 0


def _call(base_url: str, spec: EndpointSpec, timeout: float) -> Result:
    url = f"{base_url}{spec.path}"
    data = json.dumps(spec.body).encode("utf-8") if spec.body is not None else None
    req = urllib.request.Request(
        url, data=data, method=spec.method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            status = resp.status
        ok = 200 <= status < 300
    except urllib.error.HTTPError as exc:
        status = exc.code
        ok = False
    except Exception:  # noqa: BLE001 - network errors, timeouts, etc.
        status = 0
        ok = False
    return Result(ok=ok, status=status, latency_seconds=time.perf_counter() - t0)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct
    f, c = int(k), min(int(k) + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (k - f) * (ordered[c] - ordered[f])


def run_load_test(base_url: str, concurrency: int, requests_per_endpoint: int, timeout: float) -> dict[str, Aggregate]:
    endpoints = [
        EndpointSpec("health", "GET", "/health"),
        EndpointSpec("list_incidents", "GET", "/incidents"),
        EndpointSpec("report_summary", "GET", "/reports/summary"),
        EndpointSpec("pipeline_status", "GET", "/pipeline/status"),
        EndpointSpec("pipeline_run", "POST", "/pipeline/run", body={"clear_memory": True}),
    ]

    results: dict[str, Aggregate] = {spec.name: Aggregate() for spec in endpoints}

    for spec in endpoints:
        # pipeline_run is expensive/stateful -- run it serially and fewer times
        n = requests_per_endpoint if spec.name != "pipeline_run" else max(1, requests_per_endpoint // 10)
        conc = concurrency if spec.name != "pipeline_run" else min(3, concurrency)

        with ThreadPoolExecutor(max_workers=conc) as pool:
            futures = [pool.submit(_call, base_url, spec, timeout) for _ in range(n)]
            for future in as_completed(futures):
                result = future.result()
                agg = results[spec.name]
                agg.total += 1
                agg.latencies.append(result.latency_seconds)
                if not result.ok:
                    agg.errors += 1

    return results


def print_report(results: dict[str, Aggregate]) -> None:
    print(f"{'endpoint':<18}{'reqs':>6}{'errors':>8}{'p50 ms':>10}{'p95 ms':>10}{'p99 ms':>10}{'max ms':>10}{'rps':>8}")
    print("-" * 80)
    for name, agg in results.items():
        if not agg.latencies:
            continue
        p50 = _percentile(agg.latencies, 0.50) * 1000
        p95 = _percentile(agg.latencies, 0.95) * 1000
        p99 = _percentile(agg.latencies, 0.99) * 1000
        p_max = max(agg.latencies) * 1000
        total_time = sum(agg.latencies) or 1e-9
        rps = agg.total / total_time if total_time else 0.0
        print(f"{name:<18}{agg.total:>6}{agg.errors:>8}{p50:>10.2f}{p95:>10.2f}{p99:>10.2f}{p_max:>10.2f}{rps:>8.1f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Load-test the AI Cyber Attack Response API")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=100, help="requests per endpoint")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    print(f"Load-testing {args.base_url} (concurrency={args.concurrency}, requests/endpoint={args.requests})\n")
    results = run_load_test(args.base_url, args.concurrency, args.requests, args.timeout)
    print_report(results)

    total_errors = sum(agg.errors for agg in results.values())
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
