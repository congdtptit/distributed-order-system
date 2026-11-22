"""Flow C at the branch: the dish cache, merged by version (section 7 of
docs/01-business-spec.md, POS and Online side; BR10; ``menu_cache`` in section 5 of
docs/02-detailed-design.md).

- ``DishStatusChanged`` overwrites a dish only if its ``(epoch, seq)`` is greater than the one
  held (epochs first). Any message from Inventory, and every heartbeat, moves ``last_heard_at``;
  an epoch greater than the one held is noted in ``newest_epoch``.
- ``MenuSync`` fetches Inventory's snapshot when the branch starts (a start counts as
  reconnecting), when the connection to Kafka comes back, and when a greater epoch was heard.
  The snapshot is merged by the same rule, never by clearing the cache; when it brings a new
  epoch, every dish still at an older epoch moves to Hidden.
- The data is fresh while something was heard from Inventory within N minutes (section 10).
  Fresh or not, the screen decides only how to show a dish; ``POST /orders`` never looks at
  this cache (point 5 in section 8 of the design).
"""

import json
import logging
import threading
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final, cast

import psycopg

from common.clock import Clock
from common.consumer import Handler, Incoming
from order_service.sender import ConnectionStatus

log = logging.getLogger(__name__)

STALE_AFTER: Final = timedelta(minutes=5)
"""N of section 10: dish data counts as stale (proposed)."""
HIDDEN: Final = "AN"

_UPSERT: Final = """
    INSERT INTO menu_cache (dish_id, status, epoch, seq) VALUES (%s, %s, %s, %s)
    ON CONFLICT (dish_id) DO UPDATE
       SET status = EXCLUDED.status, epoch = EXCLUDED.epoch, seq = EXCLUDED.seq
     WHERE (menu_cache.epoch, menu_cache.seq) < (EXCLUDED.epoch, EXCLUDED.seq)
"""


def _version(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{what} must be a whole number, got {value!r}")
    return value


def _merge_dish(conn: psycopg.Connection[Any], dish: dict[str, Any]) -> None:
    dish_id, status = dish.get("dish_id"), dish.get("status")
    if not isinstance(dish_id, str) or status not in ("CON", "HET", "AN"):
        raise ValueError(f"not a dish status: {dish!r}")
    conn.execute(
        _UPSERT,
        (dish_id, status, _version(dish.get("epoch"), "epoch"), _version(dish.get("seq"), "seq")),
    )


def _heard(conn: psycopg.Connection[Any], epoch: int, now: datetime) -> None:
    conn.execute(
        "UPDATE menu_cache_meta SET newest_epoch = GREATEST(newest_epoch, %s),"
        " last_heard_at = GREATEST(COALESCE(last_heard_at, %s), %s)",
        (epoch, now, now),
    )


def menu_handlers(clock: Clock) -> dict[str, Handler]:
    """event_type -> handler for what a branch takes from ``menu-events``. Both are known to
    every side; the Kitchen and Inventory skip them."""

    def dish_status_changed(conn: psycopg.Connection[Any], message: Incoming) -> None:
        payload = message.envelope.payload
        # menu_cache_meta first, then the dish row: the order merge_snapshot locks them in.
        _heard(conn, _version(payload.get("epoch"), "epoch"), clock.now())
        _merge_dish(conn, payload)

    def heartbeat(conn: psycopg.Connection[Any], message: Incoming) -> None:
        _heard(conn, _version(message.envelope.payload.get("epoch"), "epoch"), clock.now())

    return {"DishStatusChanged": dish_status_changed, "Heartbeat": heartbeat}


def merge_snapshot(conn: psycopg.Connection[Any], snap: dict[str, Any], now: datetime) -> None:
    """Merge Inventory's snapshot into the cache, in the caller's transaction (committed when
    the caller's ``with`` block ends). The meta row is locked first, so two merges do not
    interleave."""
    epoch = _version(snap.get("epoch"), "epoch")
    raw = snap.get("dishes")
    if not isinstance(raw, list):
        raise ValueError("a snapshot has a list of dishes")
    dishes = [cast(dict[str, Any], d) for d in cast(list[object], raw) if isinstance(d, dict)]
    held = conn.execute("SELECT epoch FROM menu_cache_meta FOR UPDATE").fetchone()
    if held is None:
        raise RuntimeError("menu_cache_meta has no row: migration 004 creates it")
    for dish in sorted(dishes, key=lambda d: str(d.get("dish_id"))):
        _merge_dish(conn, dish)
    if epoch > int(held[0]):
        # BR10: a new generation. What the new snapshot did not bring is gone.
        conn.execute("UPDATE menu_cache SET status = %s WHERE epoch < %s", (HIDDEN, epoch))
        conn.execute("UPDATE menu_cache_meta SET epoch = %s", (epoch,))
    _heard(conn, epoch, now)


def needs_snapshot(conn: psycopg.Connection[Any]) -> bool:
    """Never fetched (epoch 0), or a greater epoch was heard than the one held."""
    row = conn.execute("SELECT epoch, newest_epoch FROM menu_cache_meta").fetchone()
    if row is None:
        raise RuntimeError("menu_cache_meta has no row: migration 004 creates it")
    return int(row[0]) == 0 or int(row[1]) > int(row[0])


def cache(conn: psycopg.Connection[Any]) -> dict[str, tuple[str, int, int]]:
    return {
        str(r[0]): (str(r[1]), int(r[2]), int(r[3]))
        for r in conn.execute("SELECT dish_id, status, epoch, seq FROM menu_cache").fetchall()
    }


@dataclass(frozen=True)
class MenuDish:
    dish_id: str
    name: str
    status: str | None
    """CON, HET, AN, or None while the cache has nothing for this dish."""


@dataclass(frozen=True)
class MenuView:
    stale: bool
    last_heard_at: datetime | None
    dishes: list[MenuDish]


def menu_view(
    conn: psycopg.Connection[Any], now: datetime, stale_after: timedelta = STALE_AFTER
) -> MenuView:
    """``GET /menu``: the branch's dish catalogue with each dish's cached status."""
    row = conn.execute("SELECT last_heard_at FROM menu_cache_meta").fetchone()
    heard: datetime | None = None if row is None else row[0]
    rows = conn.execute(
        "SELECT d.dish_id, d.name, c.status FROM dishes d"
        " LEFT JOIN menu_cache c ON c.dish_id = d.dish_id ORDER BY d.dish_id"
    ).fetchall()
    return MenuView(
        stale=heard is None or now - heard > stale_after,
        last_heard_at=heard,
        dishes=[MenuDish(str(r[0]), str(r[1]), None if r[2] is None else str(r[2])) for r in rows],
    )


def http_snapshot(base_url: str, timeout_s: float = 5.0) -> Callable[[], dict[str, Any]]:
    """Fetch ``GET /menu/snapshot`` from Inventory: the one call between services (section 6
    of the design). It travels on the branch's link to the centre, which ``bin/chaos offline``
    cuts together with Kafka."""

    def fetch() -> dict[str, Any]:
        with urllib.request.urlopen(f"{base_url}/menu/snapshot", timeout=timeout_s) as response:
            body: dict[str, Any] = json.loads(response.read())
            return body

    return fetch


class MenuSync:
    """Fetches and merges the snapshot when the cache needs it (see the module docstring)."""

    def __init__(
        self,
        connect: Callable[[], psycopg.Connection[Any]],
        fetch: Callable[[], dict[str, Any]],
        connection: Callable[[], ConnectionStatus],
        clock: Clock,
    ) -> None:
        self._connect = connect
        self._fetch = fetch
        self._connection = connection
        self._clock = clock
        self._was_connected: bool | None = None
        # A start counts as reconnecting: what was missed while down may be gone from Kafka.
        self._pending_reconnect = True

    def sync_once(self) -> bool:
        """One look; True if a snapshot was merged."""
        connected = self._connection().connected
        if connected is True and self._was_connected is False:
            self._pending_reconnect = True  # Flow C, POS side, step 2
        if connected is not None:
            self._was_connected = connected
        with self._connect() as conn:
            wanted = self._pending_reconnect or needs_snapshot(conn)
        if not wanted or connected is False:
            return False
        try:
            snap = self._fetch()
        except (OSError, ValueError) as exc:
            log.warning("menu snapshot not fetched, will try again: %s", exc)
            return False
        with self._connect() as conn:
            merge_snapshot(conn, snap, self._clock.now())
        self._pending_reconnect = False
        log.info("menu snapshot merged, epoch %s", snap.get("epoch"))
        return True

    def run(self, stop: threading.Event, every_s: float = 2.0) -> None:
        while not stop.is_set():
            try:
                self.sync_once()
            except Exception:
                log.exception("menu sync round failed; trying again")
            stop.wait(every_s)
