"""Flow C at the branch (phase 2): the dish cache merged by version, the snapshot, the new
epoch, and whether the data is fresh. Section 7 of docs/01-business-spec.md (POS and Online
side), BR10; section 5 of docs/02-detailed-design.md (``menu_cache``)."""

import itertools
import threading
from datetime import datetime, timedelta
from typing import Any

import psycopg
import pytest
from branch_support import NOW
from fastapi.testclient import TestClient

from common.api import get_clock
from common.clock import Clock, FixedClock
from common.consumer import Incoming, Source, handle_once
from common.envelope import Envelope, new_envelope
from order_service.app import app
from order_service.menu import (
    MenuSync,
    cache,
    menu_handlers,
    merge_snapshot,
    needs_snapshot,
)
from order_service.sender import ConnectionStatus

_offsets = itertools.count()


def menu_message(event_type: str, payload: dict[str, Any], at: datetime = NOW) -> Envelope:
    return new_envelope(
        event_type, order_id=None, branch_id=None, clock=FixedClock(at), payload=payload
    )


def dish(dish_id: str, status: str, epoch: int, seq: int) -> dict[str, Any]:
    return {"dish_id": dish_id, "status": status, "epoch": epoch, "seq": seq}


def hear(dsn: str, env: Envelope, clock: Clock | None = None) -> bool:
    """Deliver one menu-events message as the branch consumer would."""
    handler = menu_handlers(clock or FixedClock(NOW))[env.event_type]
    message = Incoming(env, None, Source("menu-events", 0, next(_offsets)))
    with psycopg.connect(dsn, autocommit=True) as conn:
        return handle_once(conn, handler, message)


def cached(dsn: str) -> dict[str, tuple[str, int, int]]:
    with psycopg.connect(dsn) as conn:
        return {d: (s, e, q) for d, (s, e, q) in cache(conn).items()}


def menu(api: TestClient, at: datetime) -> dict[str, Any]:
    app.dependency_overrides[get_clock] = lambda: FixedClock(at)
    response = api.get("/menu")
    assert response.status_code == 200
    return response.json()


def test_a_status_change_overwrites_only_an_older_version(bdb: str) -> None:
    """Flow C, POS side, step 1."""
    hear(bdb, menu_message("DishStatusChanged", dish("PHO_BO", "HET", 1, 4)))
    assert cached(bdb)["PHO_BO"] == ("HET", 1, 4)
    hear(bdb, menu_message("DishStatusChanged", dish("PHO_BO", "CON", 1, 3)))  # older: ignored
    assert cached(bdb)["PHO_BO"] == ("HET", 1, 4)
    hear(bdb, menu_message("DishStatusChanged", dish("PHO_BO", "CON", 1, 5)))
    assert cached(bdb)["PHO_BO"] == ("CON", 1, 5)
    hear(bdb, menu_message("DishStatusChanged", dish("PHO_BO", "HET", 2, 1)))  # epoch first
    assert cached(bdb)["PHO_BO"] == ("HET", 2, 1)


@pytest.mark.kb(19)
def test_sold_out_v6_survives_a_snapshot_saying_available_v5(bdb: str) -> None:
    """Scenario 19: POS receives a Sold out message (v6), then a snapshot with Available (v5)
    arrives later. POS keeps Sold out (v6)."""
    hear(bdb, menu_message("DishStatusChanged", dish("PHO_BO", "HET", 1, 6)))
    with psycopg.connect(bdb) as conn:
        merge_snapshot(conn, {"epoch": 1, "dishes": [dish("PHO_BO", "CON", 1, 5)]}, NOW)
    assert cached(bdb)["PHO_BO"] == ("HET", 1, 6)


@pytest.mark.kb(20)
def test_a_new_epoch_brings_the_snapshot_and_hides_what_it_left_out(bdb: str) -> None:
    """Scenario 20: Inventory is restored from a backup and increases the epoch; dish A is
    Sold out in the old generation, dish B is not in the new snapshot. A follows the new
    snapshot; B moves to Hidden."""
    with psycopg.connect(bdb) as conn:
        merge_snapshot(
            conn,
            {"epoch": 1, "dishes": [dish("PHO_BO", "CON", 1, 0), dish("TRA_DA", "CON", 1, 0)]},
            NOW,
        )
    hear(bdb, menu_message("DishStatusChanged", dish("PHO_BO", "HET", 1, 7)))  # A Sold out
    with psycopg.connect(bdb) as conn:
        assert needs_snapshot(conn) is False
    hear(bdb, menu_message("Heartbeat", {"epoch": 2, "seq": 1}))
    with psycopg.connect(bdb) as conn:
        assert needs_snapshot(conn) is True  # a heartbeat with a greater epoch

    fetched: list[int] = []

    def fetch() -> dict[str, Any]:
        fetched.append(1)
        return {"epoch": 2, "dishes": [dish("PHO_BO", "CON", 2, 1)]}  # B is not in it

    sync = MenuSync(
        lambda: psycopg.connect(bdb),
        fetch,
        lambda: ConnectionStatus(True, NOW),
        FixedClock(NOW),
    )
    sync.sync_once()
    assert fetched == [1]
    assert cached(bdb)["PHO_BO"] == ("CON", 2, 1)  # A follows the new snapshot
    assert cached(bdb)["TRA_DA"][0] == "AN"  # B moves to Hidden
    with psycopg.connect(bdb) as conn:
        assert needs_snapshot(conn) is False
    sync.sync_once()
    assert fetched == [1]  # nothing new: no second fetch


def test_the_branch_fetches_the_snapshot_on_start_and_after_reconnecting(bdb: str) -> None:
    """Flow C, POS side, step 2: on reconnecting, fetch the snapshot and merge it."""
    connected = {"value": True}
    fetched: list[int] = []

    def fetch() -> dict[str, Any]:
        fetched.append(1)
        return {"epoch": 1, "dishes": [dish("PHO_BO", "CON", 1, len(fetched))]}

    sync = MenuSync(
        lambda: psycopg.connect(bdb),
        fetch,
        lambda: ConnectionStatus(connected["value"], NOW),
        FixedClock(NOW),
    )
    sync.sync_once()
    assert fetched == [1]  # on start: never fetched
    sync.sync_once()
    assert fetched == [1]
    connected["value"] = False
    sync.sync_once()
    assert fetched == [1]  # offline: nothing to fetch from
    connected["value"] = True
    sync.sync_once()
    assert fetched == [1, 1]  # reconnected
    assert cached(bdb)["PHO_BO"] == ("CON", 1, 2)


def test_a_failed_fetch_is_tried_again(bdb: str) -> None:
    calls = {"n": 0}

    def fetch() -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("connection refused")
        return {"epoch": 1, "dishes": [dish("PHO_BO", "CON", 1, 1)]}

    sync = MenuSync(
        lambda: psycopg.connect(bdb), fetch, lambda: ConnectionStatus(True, NOW), FixedClock(NOW)
    )
    sync.sync_once()
    assert cached(bdb) == {}
    sync.sync_once()
    assert cached(bdb)["PHO_BO"] == ("CON", 1, 1)


def test_the_menu_shows_every_dish_with_its_status_and_is_stale_before_anything_is_heard(
    bdb: str, api: TestClient
) -> None:
    body = menu(api, NOW)
    assert body["stale"] is True
    assert body["last_heard_at"] is None
    by_dish = {d["dish_id"]: d for d in body["dishes"]}
    assert by_dish["PHO_BO"] == {"dish_id": "PHO_BO", "name": "Phở bò", "status": None}
    hear(bdb, menu_message("DishStatusChanged", dish("PHO_BO", "HET", 1, 1)))
    body = menu(api, NOW + timedelta(seconds=5))
    assert body["stale"] is False
    assert {d["dish_id"]: d["status"] for d in body["dishes"]}["PHO_BO"] == "HET"


@pytest.mark.kb(21)
def test_regular_heartbeats_keep_the_menu_fresh_for_ten_quiet_minutes(
    bdb: str, api: TestClient
) -> None:
    """Scenario 21: Inventory has no stock change for 10 minutes and heartbeats are regular.
    POS does not show "May be sold out": the data stays fresh."""
    for minute in range(11):
        at = NOW + timedelta(minutes=minute)
        hear(bdb, menu_message("Heartbeat", {"epoch": 1, "seq": 0}, at), FixedClock(at))
        assert menu(api, at + timedelta(seconds=30))["stale"] is False
    # Against: once the heartbeats stop, the data turns stale after N = 5 minutes.
    last = NOW + timedelta(minutes=10)
    assert menu(api, last + timedelta(minutes=5))["stale"] is False
    assert menu(api, last + timedelta(minutes=5, seconds=1))["stale"] is True


def test_a_duplicate_heartbeat_changes_nothing(bdb: str) -> None:
    env = menu_message("Heartbeat", {"epoch": 1, "seq": 0})
    assert hear(bdb, env) is True
    assert hear(bdb, env) is False  # the same event_id: processed_events (BR4)


def test_the_cache_and_the_sync_do_not_block_each_other(bdb: str) -> None:
    """A snapshot merge and a status message for the same dish at the same moment: the newer
    version wins whichever commits last."""
    for i in range(20):
        barrier = threading.Barrier(2)

        def message(seq: int = 100 + 2 * i, gate: threading.Barrier = barrier) -> None:
            gate.wait()
            hear(bdb, menu_message("DishStatusChanged", dish("PHO_BO", "HET", 1, seq)))

        def merge(seq: int = 100 + 2 * i - 1, gate: threading.Barrier = barrier) -> None:
            gate.wait()
            with psycopg.connect(bdb) as conn:
                merge_snapshot(conn, {"epoch": 1, "dishes": [dish("PHO_BO", "CON", 1, seq)]}, NOW)

        threads = [threading.Thread(target=message), threading.Thread(target=merge)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        assert cached(bdb)["PHO_BO"] == ("HET", 1, 100 + 2 * i)


def test_a_restarted_branch_fetches_the_snapshot_once_even_with_a_cache(bdb: str) -> None:
    """A start counts as reconnecting (section 5 of document 02, "Flow C at the branch in
    practice"): the messages missed while the branch was down may be gone from Kafka."""
    with psycopg.connect(bdb) as conn:
        merge_snapshot(conn, {"epoch": 1, "dishes": [dish("PHO_BO", "CON", 1, 1)]}, NOW)
        assert needs_snapshot(conn) is False
    fetched: list[int] = []

    def fetch() -> dict[str, Any]:
        fetched.append(1)
        return {"epoch": 1, "dishes": [dish("PHO_BO", "HET", 1, 2)]}

    sync = MenuSync(
        lambda: psycopg.connect(bdb), fetch, lambda: ConnectionStatus(True, NOW), FixedClock(NOW)
    )
    sync.sync_once()
    assert fetched == [1]
    assert cached(bdb)["PHO_BO"] == ("HET", 1, 2)
    sync.sync_once()
    assert fetched == [1]  # once
