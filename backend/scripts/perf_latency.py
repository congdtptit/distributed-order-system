"""Time from creating an order at a branch to seeing it Reserved there, for the performance part
of the course report (section 2 of docs/04-course-report.md). Run by bin/perf in the tools
container after the load test.

Each order goes all the way through the system: the branch's send queue, Kafka, Inventory, and
back through ``status-events.POS01``. The orders are placed one at a time; each is polled every
20 ms through ``GET /orders/{id}`` until it leaves ``CHO_KHO``. Writes /perf/results/latency.json.

Environment: ``PERF_ORDERS`` (default 30), ``PERF_BRANCH_URL`` (default http://pos01:8000).
"""

import json
import os
import statistics
import time
import urllib.request
from pathlib import Path
from typing import Any

POLL_S = 0.02
TIMEOUT_S = 30.0
OUT = Path("/perf/results/latency.json")


def call(method: str, url: str, body: Any = None) -> Any:
    request = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def one_order(base: str) -> tuple[float, str]:
    started = time.monotonic()
    order = call("POST", f"{base}/orders", {"items": [{"dish_id": "TRA_DA", "quantity": 1}]})
    while True:
        status = call("GET", f"{base}/orders/{order['order_id']}")["status"]
        elapsed = time.monotonic() - started
        if status != "CHO_KHO" or elapsed > TIMEOUT_S:
            return elapsed * 1000, status
        time.sleep(POLL_S)


def main() -> None:
    count = int(os.environ.get("PERF_ORDERS", "30"))
    base = os.environ.get("PERF_BRANCH_URL", "http://pos01:8000")
    samples = [one_order(base) for _ in range(count)]
    reserved = sorted(ms for ms, status in samples if status == "DA_GIU")
    by_status: dict[str, int] = {}
    for _, status in samples:
        by_status[status] = by_status.get(status, 0) + 1
    result: dict[str, Any] = {
        "orders": count,
        "by_status": by_status,
        "poll_ms": POLL_S * 1000,
        "reserved_ms": {
            "min": round(reserved[0]),
            "mean": round(statistics.fmean(reserved)),
            "median": round(statistics.median(reserved)),
            "p95": round(reserved[max(0, round(0.95 * len(reserved)) - 1)]),
            "max": round(reserved[-1]),
        }
        if reserved
        else None,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
