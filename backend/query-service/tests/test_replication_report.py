"""Scenario 55 on the running cluster (tier 3): replication from POS01 to the Central Order
Replica is cut while POS01 and POS02 keep taking orders, then reconnected.

The cut is ``bin/chaos cut-replication pos01``: ``pos01-db`` leaves ``replication-net``, so the
central DB's subscription cannot reach it, while the ``pos01`` service still writes to its DB
and answers its API. Needs the ``full`` profile (``pos02``)."""

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

import psycopg
import pytest

pytestmark = pytest.mark.tier3

QUERY = "http://query:8000"
BRANCH_API = {"POS01": "http://pos01:8000", "POS02": "http://pos02:8000"}
POS01_DB = "postgresql://app:app@pos01-db:5432/branch"
CENTRAL_DB = "postgresql://app:app@central-db:5432/central"
BEAT_S = 5


class Chaos(Protocol):
    """The ``chaos`` fixture of backend/conftest.py."""

    def disconnect(self, service: str, network: str = "kafka-net") -> None: ...
    def connect(self, service: str, network: str = "kafka-net") -> None: ...


def http(method: str, url: str, body: Any = None) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def wait_for(what: str, timeout_s: float, check: Callable[[], Any]) -> Any:
    deadline = time.monotonic() + timeout_s
    while True:
        value = check()
        if value:
            return value
        assert time.monotonic() < deadline, f"timed out waiting for {what}"
        time.sleep(0.5)


def report() -> dict[str, Any]:
    status, body = http("GET", f"{QUERY}/reports/summary")
    assert status == 200, body
    return {line["branch_id"]: line for line in body["branches"]}


def as_of(line: dict[str, Any]) -> datetime | None:
    value = line["data_as_of"]
    return None if value is None else datetime.fromisoformat(value)


def place(branch: str) -> str:
    status, order = http(
        "POST", f"{BRANCH_API[branch]}/orders", {"items": [{"dish_id": "TRA_DA", "quantity": 1}]}
    )
    assert status == 201, order
    return order["order_id"]


def at_central(order_ids: list[str]) -> int:
    with psycopg.connect(CENTRAL_DB) as conn:
        row = conn.execute(
            "SELECT count(*) FROM orders WHERE order_id = ANY(%s::uuid[])", (order_ids,)
        ).fetchone()
    assert row is not None
    return int(row[0])


def figures_at_pos01() -> tuple[datetime, dict[str, int], list[dict[str, Any]]]:
    """The branch DB's own figures, in the report's shape, and the branch clock they hold at."""
    with psycopg.connect(POS01_DB) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        now_row = conn.execute("SELECT now()").fetchone()
        assert now_row is not None
        rows = conn.execute(
            "SELECT status, close_reason, count(*)::int FROM orders "
            "GROUP BY 1, 2 ORDER BY 1, 2 NULLS LAST"
        ).fetchall()
    by_status = dict.fromkeys(["CHO_KHO", "DA_GIU", "HOAN_TAT", "DA_HUY", "THAT_BAI"], 0)
    reasons: list[dict[str, Any]] = []
    for status, reason, count in rows:
        by_status[status] += count
        if status in ("DA_HUY", "THAT_BAI"):
            reasons.append({"status": status, "reason_code": reason, "count": count})
    order = ["DA_HUY", "THAT_BAI"]
    reasons.sort(key=lambda r: (order.index(r["status"]), r["reason_code"] or ""))
    return now_row[0], by_status, reasons


@pytest.mark.kb(55)
def test_cutting_replication_from_pos01_stops_only_its_data_as_of_time(chaos: Chaos) -> None:
    for branch, url in BRANCH_API.items():
        status, _ = http("GET", f"{url}/health")
        assert status == 200, f"{branch} is not running: docker compose --profile full up -d"

    # Both branches' data is current before the cut.
    def both_fresh() -> bool:
        lines = report()
        return all((lines[b]["data_age_s"] or 1e9) < 2 * BEAT_S for b in BRANCH_API)

    wait_for("both branches to replicate", 30, both_fresh)

    chaos.disconnect("pos01-db", "replication-net")
    time.sleep(1)  # a beat already on the wire may still land
    frozen = as_of(report()["POS01"])
    pos02_at_cut = as_of(report()["POS02"])
    assert frozen is not None
    assert pos02_at_cut is not None

    # Both branches keep taking orders.
    pos01_orders = [place("POS01"), place("POS01")]
    pos02_orders = [place("POS02"), place("POS02")]

    # POS02 keeps beating; wait for three of its beats to arrive.
    def pos02_moved() -> dict[str, Any] | None:
        lines = report()
        pos02 = as_of(lines["POS02"])
        assert pos02 is not None
        return lines if (pos02 - pos02_at_cut).total_seconds() >= 3 * BEAT_S else None

    lines = wait_for("POS02's data as of to move on", 60, pos02_moved)
    # While it is cut, the report can still be viewed ...
    assert set(lines) >= {"POS01", "POS02"}
    # ... the "data as of" marker of POS01 stops ...
    assert as_of(lines["POS01"]) == frozen
    assert lines["POS01"]["data_age_s"] > 3 * BEAT_S
    # ... while that of POS02 keeps moving.
    assert lines["POS02"]["data_age_s"] < 2 * BEAT_S
    # The orders POS01 took meanwhile have not reached the central DB; POS02's have.
    assert at_central(pos01_orders) == 0
    assert wait_for("POS02's orders at the central DB", 30, lambda: at_central(pos02_orders) == 2)

    chaos.connect("pos01-db", "replication-net")

    # After reconnection, the POS01 figures match the branch's DB. Read the branch's figures,
    # wait until the report's data as of has passed that moment, then compare; if the branch
    # changed in between (an order moving on through Inventory), read again.
    def pos01_matches() -> bool:
        read_at, by_status, reasons = figures_at_pos01()

        def beat_after_read() -> dict[str, Any] | None:
            line = report()["POS01"]
            reached = as_of(line)
            return line if reached is not None and reached >= read_at else None

        line = wait_for("a POS01 beat after the branch was read", 60, beat_after_read)
        return (
            line["by_status"] == by_status
            and line["reasons"] == reasons
            and line["total"] == sum(by_status.values())
        )

    wait_for("the POS01 figures to match the branch DB", 120, pos01_matches)
    assert at_central(pos01_orders) == 2
