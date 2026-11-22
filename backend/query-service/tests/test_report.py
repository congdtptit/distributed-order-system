"""``GET /reports/summary``: Management's report from the Central Order Replica (section 8 of
docs/01-business-spec.md; sections 5 and 6 of docs/02-detailed-design.md). The tests write the
rows that logical replication would have applied; replication itself is scenario 55, on the
running cluster (test_replication_report.py)."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from fastapi.testclient import TestClient

T0 = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
ZERO = {"CHO_KHO": 0, "DA_GIU": 0, "HOAN_TAT": 0, "DA_HUY": 0, "THAT_BAI": 0}


def replicated(
    dsn: str,
    branch: str,
    status: str,
    reason: str | None = None,
    *,
    cancel_flag: str = "KHONG",
) -> None:
    rank = {"CHO_KHO": 0, "DA_GIU": 1}.get(status, 2)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            """INSERT INTO orders (order_id, branch_id, status, status_rank, close_reason,
                                   cancel_flag, items, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                uuid.uuid4(),
                branch,
                status,
                rank,
                reason,
                cancel_flag,
                json.dumps([{"dish_id": "TRA_DA", "name": "Trà đá", "quantity": 1}]),
                T0,
            ),
        )


def heartbeat(dsn: str, branch: str, age: timedelta) -> datetime:
    """The branch's beat as it reached the central DB, ``age`` before the central clock."""
    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            "INSERT INTO replication_heartbeat (branch_id, beat_at) VALUES (%s, now() - %s) "
            "RETURNING beat_at",
            (branch, age),
        ).fetchone()
    assert row is not None
    return row[0]


def summary(api: TestClient) -> dict[str, Any]:
    response = api.get("/reports/summary")
    assert response.status_code == 200
    return response.json()


def branch(report: dict[str, Any], branch_id: str) -> dict[str, Any]:
    [line] = [b for b in report["branches"] if b["branch_id"] == branch_id]
    return line


def test_counts_orders_by_status_for_each_branch(api: TestClient, cdb: str) -> None:
    for status in ["CHO_KHO", "DA_GIU", "DA_GIU", "HOAN_TAT"]:
        replicated(cdb, "POS01", status)
    replicated(cdb, "POS02", "HOAN_TAT")
    report = summary(api)
    assert branch(report, "POS01")["by_status"] == {
        **ZERO,
        "CHO_KHO": 1,
        "DA_GIU": 2,
        "HOAN_TAT": 1,
    }
    assert branch(report, "POS01")["total"] == 4
    assert branch(report, "POS02")["by_status"] == {**ZERO, "HOAN_TAT": 1}
    assert branch(report, "ONLINE")["by_status"] == ZERO


def test_counts_cancelled_and_failed_orders_by_reason(api: TestClient, cdb: str) -> None:
    """Cancel reasons (customer and Kitchen rejection) and failure reasons, per branch."""
    replicated(cdb, "POS01", "DA_HUY", "CHANGED_MIND")
    replicated(cdb, "POS01", "DA_HUY", "CHANGED_MIND")
    replicated(cdb, "POS01", "DA_HUY", "EQUIPMENT_FAILURE")
    replicated(cdb, "POS01", "THAT_BAI", "INSUFFICIENT_INGREDIENTS")
    replicated(cdb, "POS01", "HOAN_TAT")
    replicated(cdb, "POS02", "THAT_BAI", "ORDER_EXPIRED")
    report = summary(api)
    assert branch(report, "POS01")["reasons"] == [
        {"status": "DA_HUY", "reason_code": "CHANGED_MIND", "count": 2},
        {"status": "DA_HUY", "reason_code": "EQUIPMENT_FAILURE", "count": 1},
        {"status": "THAT_BAI", "reason_code": "INSUFFICIENT_INGREDIENTS", "count": 1},
    ]
    assert branch(report, "POS02")["reasons"] == [
        {"status": "THAT_BAI", "reason_code": "ORDER_EXPIRED", "count": 1},
    ]
    assert branch(report, "ONLINE")["reasons"] == []


def test_a_pending_cancel_is_not_counted_as_cancelled(api: TestClient, cdb: str) -> None:
    """Section 8 of the specification: only the branch's order statuses count; an order the
    Kitchen will not cook is still Awaiting Inventory until Inventory answers."""
    replicated(cdb, "POS01", "CHO_KHO", cancel_flag="BEP_KHONG_NAU")
    replicated(cdb, "POS01", "DA_GIU", cancel_flag="DANG_YEU_CAU")
    line = branch(summary(api), "POS01")
    assert line["by_status"] == {**ZERO, "CHO_KHO": 1, "DA_GIU": 1}
    assert line["reasons"] == []


def test_gives_each_branch_its_own_data_as_of_time(api: TestClient, cdb: str) -> None:
    pos01 = heartbeat(cdb, "POS01", timedelta(minutes=3))
    pos02 = heartbeat(cdb, "POS02", timedelta(seconds=4))
    report = summary(api)
    generated = datetime.fromisoformat(report["generated_at"])
    line = branch(report, "POS01")
    assert datetime.fromisoformat(line["data_as_of"]) == pos01
    assert line["data_age_s"] == (generated - pos01).total_seconds()
    assert 179 < line["data_age_s"] < 185
    line = branch(report, "POS02")
    assert datetime.fromisoformat(line["data_as_of"]) == pos02
    assert 3 < line["data_age_s"] < 10


def test_lists_every_configured_branch_even_before_its_data_arrives(api: TestClient) -> None:
    report = summary(api)
    assert [b["branch_id"] for b in report["branches"]] == ["POS01", "POS02", "ONLINE"]
    for line in report["branches"]:
        assert line["data_as_of"] is None
        assert line["data_age_s"] is None
        assert line["total"] == 0
        assert line["by_status"] == ZERO


def test_a_branch_found_in_the_data_but_not_configured_is_listed_last(
    api: TestClient, cdb: str
) -> None:
    replicated(cdb, "POS03", "HOAN_TAT")
    heartbeat(cdb, "POS04", timedelta(seconds=1))
    report = summary(api)
    assert [b["branch_id"] for b in report["branches"]] == [
        "POS01",
        "POS02",
        "ONLINE",
        "POS03",
        "POS04",
    ]
    assert branch(report, "POS03")["by_status"] == {**ZERO, "HOAN_TAT": 1}
