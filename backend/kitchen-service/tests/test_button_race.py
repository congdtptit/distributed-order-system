"""Scenario 52 (tier 2): Reject and Start cooking pressed on the same Queued ticket at the same
moment, on two connections, many times. Both sides run for real: the order is reserved by
Inventory's handler, and whatever the Kitchen sends to ``stock-commands`` is delivered back to
Inventory, to check that the reservation leaves Held exactly once."""

import json
import threading
import uuid
from collections.abc import Callable
from typing import Any

import inventory_support as inv
import psycopg
import pytest
from kitchen_support import NOW, deliver, outbox, record

from common import reasons
from common.clock import FixedClock
from common.envelope import Envelope, decode
from kitchen_service.tickets import ActionError, reject, start_cooking

RUNS = 100
CLOCK = FixedClock(NOW)


def as_envelope(payload: dict[str, Any]) -> Envelope:
    return decode(json.dumps(payload).encode())


def press_both(kdb_conns: list[psycopg.Connection[Any]], order_id: uuid.UUID) -> list[str]:
    """Start cooking on one connection, Reject on the other, released together. Returns what
    happened to each: "won" or the HTTP code of the refusal."""
    barrier = threading.Barrier(2)
    results: list[str] = ["", ""]

    def press(i: int) -> None:
        conn = kdb_conns[i]
        barrier.wait()
        try:
            with conn.transaction():
                if i == 0:
                    start_cooking(conn, order_id, CLOCK)
                else:
                    reject(conn, order_id, reasons.EQUIPMENT_FAILURE, [], CLOCK)
            results[i] = "won"
        except ActionError as exc:
            results[i] = str(exc.status_code)

    threads = [threading.Thread(target=press, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    return results


@pytest.mark.kb(52)
def test_reject_and_start_cooking_at_the_same_time_one_wins_and_held_is_left_once(
    migrated: Callable[[str], str],
) -> None:
    """Scenario 52: two staff members press Reject and Start cooking on the same Queued ticket
    at the same time. Exactly one operation wins; the reservation leaves Held exactly once, to
    consumed or to released."""
    kdb = migrated("kitchen-service")
    idb = inv.seeded(migrated("inventory-service"))
    conns = [psycopg.connect(kdb, autocommit=True) for _ in range(2)]
    wins = {"start": 0, "reject": 0}
    try:
        for _ in range(RUNS):
            inv.set_available(idb, "LA_TRA", inv.D("1"))
            inv.set_available(idb, "DA", inv.D("10"))
            order = inv.order_created(items=[("TRA_DA", 1)])
            inv.deliver(idb, order)
            [to_kitchen] = [
                r
                for r in inv.outbox(idb)
                if r.topic == "kitchen-orders" and r.causation_id == str(order.event_id)
            ]
            assert order.order_id is not None
            with psycopg.connect(idb) as c:
                payload = c.execute(
                    "SELECT payload FROM outbox_events WHERE event_id = %s",
                    (uuid.UUID(to_kitchen.event_id),),
                ).fetchone()
            assert payload is not None
            deliver(kdb, as_envelope(payload[0]))

            results = press_both(conns, order.order_id)
            # Exactly one operation wins; the other is refused as a lost race (409).
            assert sorted(results) == ["409", "won"]
            winner = "start" if results[0] == "won" else "reject"
            wins[winner] += 1
            rec = record(kdb, order.order_id)
            assert rec is not None and rec["status"] == (
                "DANG_NAU" if winner == "start" else "DA_HUY"
            )

            # Exactly one command for this order goes to Inventory, matching the winner.
            commands = [
                s
                for s in outbox(kdb)
                if s.topic == "stock-commands" and s.key == str(order.order_id)
            ]
            assert [c.event_type for c in commands] == (
                ["StockConsumed"] if winner == "start" else ["ReleaseRequested"]
            )
            with psycopg.connect(kdb) as c:
                rows = c.execute(
                    "SELECT payload FROM outbox_events"
                    " WHERE topic = 'stock-commands' AND msg_key = %s",
                    (str(order.order_id),),
                ).fetchall()
            for (p,) in rows:
                inv.deliver(idb, as_envelope(p))

            # The reservation leaves Held exactly once, to consumed or to released.
            status = inv.order_record(idb, order.order_id)
            assert status is not None and status[0] == (
                "DA_DUNG" if winner == "start" else "DA_TRA"
            )
            outcomes = set(inv.line_outcomes(idb, order.order_id).values())
            assert outcomes == ({"DA_DUNG"} if winner == "start" else {"DA_HOAN"})
            inv.assert_invariants(idb)
    finally:
        for conn in conns:
            conn.close()
    # Both orders of arrival were exercised (not a test of one fixed order).
    assert wins["start"] > 0 and wins["reject"] > 0, wins
