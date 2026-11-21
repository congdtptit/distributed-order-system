"""Scenario 42 (tier 2): two orders competing for one ingredient at the same moment, on two
connections, repeated many times. Section 13.4 of docs/01-business-spec.md: the conditional
UPDATE in ascending ingredient order is what keeps stock from going negative."""

import threading
from collections.abc import Callable
from typing import Any

import psycopg
import pytest
from inventory_support import (
    D,
    assert_invariants,
    deliver,
    order_created,
    order_record,
    reservations,
    seeded,
    set_available,
    stock,
)

from common.envelope import Envelope

RUNS = 100


def race(
    dsn: str, conns: list[psycopg.Connection[Any]], orders: list[Envelope]
) -> list[BaseException]:
    """Deliver ``orders[i]`` on ``conns[i]``, all released at the same moment."""
    barrier = threading.Barrier(len(orders))
    errors: list[BaseException] = []

    def run(i: int) -> None:
        try:
            barrier.wait()
            deliver(dsn, orders[i], conn=conns[i])
        except BaseException as exc:  # surfaced to the test
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(orders))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    return errors


@pytest.mark.kb(42)
def test_two_orders_racing_for_one_ingredient_one_reserved_one_failed(
    migrated: Callable[[str], str],
) -> None:
    """Scenario 42: two orders arrive at the same time at two Inventory instances, both
    needing the same ingredient, with total demand exceeding available stock. Exactly one
    order is Reserved and the other is Failed; available stock is not negative; no order is
    partially reserved.

    Two instances are two processes on one DB; here they are two threads with their own
    connections, started together by a barrier. The check with two real instances on Kafka
    is a supplement in step 7 (point 6 in section 8 of document 02)."""
    dsn = seeded(migrated("inventory-service"))
    conns = [psycopg.connect(dsn, autocommit=True) for _ in range(2)]
    try:
        for _ in range(RUNS):
            # BUN_CHA needs BUN 0.2, THIT_LON 0.15, RAU_SONG 0.05: room for one order only,
            # because of THIT_LON. The other two are refilled so that every run starts alike.
            set_available(dsn, "BUN", D("10"))
            set_available(dsn, "RAU_SONG", D("3"))
            set_available(dsn, "THIT_LON", D("0.2"))
            before = stock(dsn)
            orders = [order_created(items=[("BUN_CHA", 1)]) for _ in range(2)]
            errors = race(dsn, conns, orders)
            assert errors == []

            statuses = sorted(
                str(r[0]) for r in (order_record(dsn, o.order_id) for o in orders) if r
            )
            # Exactly one order is Reserved and the other is Failed.
            assert statuses == ["DANG_GIU", "THAT_BAI"]
            after = stock(dsn)
            # Available stock is not negative; exactly one portion left stock.
            assert after["THIT_LON"].available == D("0.05")
            assert all(s.available >= 0 for s in after.values())
            for ingredient, q in (
                ("BUN", D("0.2")),
                ("THIT_LON", D("0.15")),
                ("RAU_SONG", D("0.05")),
            ):
                assert after[ingredient].available == before[ingredient].available - q
            # No order is partially reserved: the winner holds all three lines, the loser none.
            held = sorted(len(reservations(dsn, o.order_id)) for o in orders)
            assert held == [0, 3]
            assert_invariants(dsn)
    finally:
        for conn in conns:
            conn.close()
