"""Races at the branch (tier 2): two operations on two connections released together, many
times, on a real PostgreSQL. Section 5 of docs/02-detailed-design.md: writes (1) and (2) lock
the same send-queue row; write (2) and write (3) lock the same ``orders`` row."""

import threading
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from branch_support import (
    NOW,
    deliver,
    entries,
    mark_attempted,
    order_row,
    place,
    status_message,
)

from common.clock import FixedClock
from order_service.orders import CancelResult, OrderClosed, cancel_order
from order_service.sender import SendQueue

RUNS = 100
CLOCK = FixedClock(NOW)


class NoLink:
    """The sender's Kafka side is not part of write (1); these races never send."""

    def probe(self, timeout_s: float = 2.0) -> bool:
        raise AssertionError("not used")

    def send_all(self, messages: object) -> list[bool]:
        raise AssertionError("not used")


def race(actions: list[Callable[[], Any]]) -> list[Any]:
    barrier = threading.Barrier(len(actions))
    results: list[Any] = [None] * len(actions)
    errors: list[BaseException] = []

    def run(i: int) -> None:
        barrier.wait()
        try:
            results[i] = actions[i]()
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(actions))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert not errors, errors
    return results


@pytest.fixture
def pair(bdb: str) -> Iterator[list[psycopg.Connection[Any]]]:
    conns = [psycopg.connect(bdb, autocommit=True) for _ in range(2)]
    yield conns
    for c in conns:
        c.close()


def press(conn: psycopg.Connection[Any], order_id: uuid.UUID) -> Callable[[], CancelResult]:
    """The cashier's cancel: write (2) in one transaction."""

    def act() -> CancelResult:
        with conn.transaction():
            return cancel_order(conn, "POS01", order_id, "CHANGED_MIND", CLOCK)

    return act


@pytest.mark.kb(37)
def test_cancel_and_the_sender_picking_up_the_entry_exactly_one_wins(
    bdb: str, pair: list[psycopg.Connection[Any]]
) -> None:
    """Scenario 37: the cashier presses cancel at the moment the sender picks up a create-order
    entry that was never attempted. Either the order is cancelled here and the entry is gone,
    so the sender has nothing to send; or the entry carries the flag and the cancel request
    goes to the Kitchen."""
    queue = SendQueue(lambda: psycopg.connect(bdb), NoLink(), CLOCK)
    outcomes = {"local": 0, "kitchen": 0}
    for _ in range(RUNS):
        order_id = place(bdb)
        [entry] = entries(bdb, order_id)
        entry_id: int = entry["id"]
        cancelled, started = race(
            [
                press(pair[0], order_id),
                lambda entry_id=entry_id: queue.start_attempts(pair[1], [entry_id]),
            ]
        )
        row = order_row(bdb, order_id)
        assert row is not None
        left = entries(bdb, order_id)
        if cancelled.local:
            outcomes["local"] += 1
            assert started == set()  # write (1) found no row: nothing will be sent
            assert left == []
            assert (row["status"], row["cancel_flag"]) == ("DA_HUY", "KHONG")
        else:
            outcomes["kitchen"] += 1
            assert started == {entry["id"]}
            assert [(e["kind"], e["attempted"]) for e in left] == [
                ("TAO_DON", True),
                ("HUY", False),
            ]
            assert (row["status"], row["cancel_flag"]) == ("CHO_KHO", "DANG_YEU_CAU")
    assert outcomes["local"] > 0 and outcomes["kitchen"] > 0, outcomes


def test_two_quick_presses_queue_one_cancel_request(
    bdb: str, pair: list[psycopg.Connection[Any]]
) -> None:
    """Write (2) locks the ``orders`` row first: the second press sees the flag and stops, so
    an attempted order never gets two cancel entries."""
    for _ in range(RUNS):
        order_id = place(bdb)
        mark_attempted(bdb, order_id)
        first, second = race([press(pair[0], order_id), press(pair[1], order_id)])
        assert not first.local and not second.local
        assert [e["kind"] for e in entries(bdb, order_id)] == ["TAO_DON", "HUY"]


def test_two_quick_presses_on_an_unattempted_order_cancel_it_once(
    bdb: str, pair: list[psycopg.Connection[Any]]
) -> None:
    """The first press cancels locally; the second sees a terminal order (409)."""

    def guarded(conn: psycopg.Connection[Any], order_id: uuid.UUID) -> Callable[[], str]:
        def act() -> str:
            try:
                return "local" if press(conn, order_id)().local else "kitchen"
            except OrderClosed:
                return "closed"

        return act

    for _ in range(RUNS):
        order_id = place(bdb)
        results = race([guarded(pair[0], order_id), guarded(pair[1], order_id)])
        assert sorted(results) == ["closed", "local"]
        assert entries(bdb, order_id) == []


def test_a_terminal_status_arriving_during_a_cancel_leaves_no_flag(
    bdb: str, pair: list[psycopg.Connection[Any]]
) -> None:
    """Writes (2) and (3) lock the same ``orders`` row: whichever runs first, a Completed order
    never keeps the "Cancel requested" flag."""

    def cashier(order_id: uuid.UUID) -> Callable[[], str]:
        def act() -> str:
            try:
                press(pair[0], order_id)()
                return "requested"
            except OrderClosed:
                return "closed"

        return act

    def completed(order_id: uuid.UUID) -> Callable[[], None]:
        def act() -> None:
            deliver(bdb, status_message("OrderCompleted", order_id), conn=pair[1])

        return act

    seen: set[str] = set()
    for _ in range(RUNS):
        order_id = place(bdb)
        mark_attempted(bdb, order_id, sent=True)
        result, _ = race([cashier(order_id), completed(order_id)])
        seen.add(result)
        row = order_row(bdb, order_id)
        assert row is not None
        assert (row["status"], row["cancel_flag"]) == ("HOAN_TAT", "KHONG")
    assert seen == {"requested", "closed"}, seen
