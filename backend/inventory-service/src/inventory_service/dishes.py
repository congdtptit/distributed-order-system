"""Dish status (Flow C): computing it, its version, the snapshot and the epoch bump.

Section 3.4 of docs/01-business-spec.md gives the status: Available (CON) when every recipe
line has enough available stock for one portion and no ingredient is flagged for stock check;
Sold out (HET) otherwise; Hidden (AN) when the dish has no recipe. Section 3 of
docs/02-detailed-design.md gives the rest:

- **Lock order**: the order row, the ``stock`` rows (ascending), the ``dish_status`` rows
  (ascending), ``menu_version`` last. ``recompute_dishes`` runs after the caller has written
  ``stock`` and before anything that takes a version (``emit_check_changed``).
- **Computing**: lock the ``dish_status`` rows of the affected dishes first, then read the
  stock. Reading first would let two transactions that change two ingredients of one dish miss
  each other's change.
- **Version**: a dish that changes status takes the next ``(epoch, seq)`` from
  ``menu_version`` and is announced with ``DishStatusChanged`` on ``menu-events``, keyed by the
  dish. A dish whose status does not change is not announced, even if its stock changed.

The starting rows carry ``(epoch, 0)``, a version older than any change, and are not
announced: a branch fetches the snapshot when it starts.
"""

import logging
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Final

import psycopg

from common.clock import Clock
from common.envelope import new_envelope
from common.outbox import enqueue
from common.topics import MENU_EVENTS
from inventory_service.checks import next_version

log = logging.getLogger(__name__)

HEARTBEAT_EVERY_S: Final = 60.0
"""Section 10 of the specification: the heartbeat interval (proposed)."""

AVAILABLE: Final = "CON"
SOLD_OUT: Final = "HET"
HIDDEN: Final = "AN"

_COMPUTED: Final = """
    SELECT d.dish_id,
           CASE WHEN count(r.ingredient_id) = 0 THEN 'AN'
                WHEN bool_and(s.available >= r.quantity AND NOT s.needs_check) THEN 'CON'
                ELSE 'HET' END
      FROM unnest(%s::text[]) AS d(dish_id)
      LEFT JOIN recipes r ON r.dish_id = d.dish_id
      LEFT JOIN stock s ON s.ingredient_id = r.ingredient_id
     GROUP BY d.dish_id
"""


@dataclass(frozen=True)
class DishVersion:
    dish_id: str
    status: str
    epoch: int
    seq: int


@dataclass(frozen=True)
class Snapshot:
    epoch: int
    dishes: list[DishVersion]


def _computed(conn: psycopg.Connection[Any], dish_ids: list[str]) -> dict[str, str]:
    return {str(r[0]): str(r[1]) for r in conn.execute(_COMPUTED, (dish_ids,)).fetchall()}


def ensure_dish_status(conn: psycopg.Connection[Any]) -> None:
    """Give every dish of the recipes a ``dish_status`` row if it has none, at the current
    epoch and seq 0, without announcing it. Runs on every start, in the caller's transaction."""
    missing = [
        str(r[0])
        for r in conn.execute(
            "SELECT DISTINCT r.dish_id FROM recipes r"
            " WHERE NOT EXISTS (SELECT 1 FROM dish_status d WHERE d.dish_id = r.dish_id)"
            " ORDER BY 1"
        ).fetchall()
    ]
    if not missing:
        return
    row = conn.execute("SELECT epoch FROM menu_version").fetchone()
    if row is None:
        raise RuntimeError("menu_version has no row: ensure_menu_version runs at start")
    for dish_id, status in sorted(_computed(conn, missing).items()):
        conn.execute(
            "INSERT INTO dish_status (dish_id, status, epoch, seq) VALUES (%s, %s, %s, 0)"
            " ON CONFLICT (dish_id) DO NOTHING",
            (dish_id, status, int(row[0])),
        )


def recompute_dishes(
    conn: psycopg.Connection[Any],
    ingredient_ids: Iterable[str],
    clock: Clock,
    dish_ids: Iterable[str] = (),
) -> list[DishVersion]:
    """Recompute the dishes that use ``ingredient_ids``, after the caller changed their stock,
    in the caller's transaction, plus ``dish_ids`` by name: a recipe change (Flow C, step 1)
    names its dish, since a removed recipe no longer leads from an ingredient to the dish.
    Returns the dishes whose status changed (each announced)."""
    ingredients = sorted(set(ingredient_ids))
    named = sorted(set(dish_ids))
    if not ingredients and not named:
        return []
    locked = conn.execute(
        "SELECT dish_id, status FROM dish_status WHERE dish_id = ANY(%s) OR dish_id IN"
        " (SELECT dish_id FROM recipes WHERE ingredient_id = ANY(%s))"
        " ORDER BY dish_id FOR UPDATE",
        (named, ingredients),
    ).fetchall()
    held = {str(r[0]): str(r[1]) for r in locked}
    if not held:
        return []
    changed: list[DishVersion] = []
    computed = _computed(conn, sorted(held))  # read only once the rows are locked
    for dish_id in sorted(held):
        status = computed[dish_id]
        if status == held[dish_id]:
            continue
        epoch, seq = next_version(conn)  # menu_version, locked last
        conn.execute(
            "UPDATE dish_status SET status = %s, epoch = %s, seq = %s WHERE dish_id = %s",
            (status, epoch, seq, dish_id),
        )
        version = DishVersion(dish_id, status, epoch, seq)
        _announce(conn, version, clock)
        changed.append(version)
    return changed


def _announce(conn: psycopg.Connection[Any], version: DishVersion, clock: Clock) -> None:
    env = new_envelope(
        "DishStatusChanged",
        order_id=None,
        branch_id=None,
        clock=clock,
        payload={
            "dish_id": version.dish_id,
            "status": version.status,
            "epoch": version.epoch,
            "seq": version.seq,
        },
    )
    enqueue(conn, MENU_EVENTS, env, key=version.dish_id)


def snapshot(conn: psycopg.Connection[Any]) -> Snapshot:
    """``GET /menu/snapshot``: every dish with its status and version, and the current epoch,
    read in one statement."""
    rows = conn.execute(
        "SELECT m.epoch, d.dish_id, d.status, d.epoch, d.seq"
        " FROM menu_version m LEFT JOIN dish_status d ON TRUE ORDER BY d.dish_id"
    ).fetchall()
    if not rows:
        raise RuntimeError("menu_version has no row: ensure_menu_version runs at start")
    return Snapshot(
        epoch=int(rows[0][0]),
        dishes=[
            DishVersion(str(r[1]), str(r[2]), int(r[3]), int(r[4]))
            for r in rows
            if r[1] is not None
        ],
    )


def bump_epoch(conn: psycopg.Connection[Any], clock: Clock) -> int:
    """``POST /admin/epoch/bump``, after Inventory is restored from a backup (section 3 of
    document 02, "Bumping epoch"). One transaction: lock every ``dish_status`` row, raise epoch
    and seq, then recompute and rewrite every row with the new version, unchanged dishes too.
    Every ingredient's flag is sent again so the Kitchen has the new generation; no
    ``DishStatusChanged`` is sent: branches see the new epoch in the next heartbeat and fetch
    the snapshot. Returns the new epoch."""
    dish_ids = [
        str(r[0])
        for r in conn.execute(
            "SELECT dish_id FROM dish_status ORDER BY dish_id FOR UPDATE"
        ).fetchall()
    ]
    row = conn.execute(
        "UPDATE menu_version SET epoch = epoch + 1, seq = seq + 1 RETURNING epoch, seq"
    ).fetchone()
    if row is None:
        raise RuntimeError("menu_version has no row: ensure_menu_version runs at start")
    epoch, seq = int(row[0]), int(row[1])
    for dish_id, status in _computed(conn, dish_ids).items():
        conn.execute(
            "UPDATE dish_status SET status = %s, epoch = %s, seq = %s WHERE dish_id = %s",
            (status, epoch, seq, dish_id),
        )
    for ingredient_id, needs_check in conn.execute(
        "SELECT ingredient_id, needs_check FROM stock ORDER BY ingredient_id"
    ).fetchall():
        _resend_flag(conn, str(ingredient_id), bool(needs_check), epoch, seq, clock)
    return epoch


def _resend_flag(
    conn: psycopg.Connection[Any],
    ingredient_id: str,
    needs_check: bool,
    epoch: int,
    seq: int,
    clock: Clock,
) -> None:
    """``IngredientCheckChanged`` at the bump's own version: ``emit_check_changed`` would take
    a new seq per ingredient, but the bump rewrites the whole generation at one version."""
    env = new_envelope(
        "IngredientCheckChanged",
        order_id=None,
        branch_id=None,
        clock=clock,
        payload={
            "ingredient_id": ingredient_id,
            "needs_check": needs_check,
            "epoch": epoch,
            "seq": seq,
        },
    )
    enqueue(conn, MENU_EVENTS, env, key=ingredient_id)


def emit_heartbeat(conn: psycopg.Connection[Any], clock: Clock) -> None:
    """``Heartbeat`` with the current ``(epoch, seq)``, keyed ``heartbeat`` (section 2 of
    document 02). It reads ``menu_version`` without locking it: a heartbeat changes nothing."""
    row = conn.execute("SELECT epoch, seq FROM menu_version").fetchone()
    if row is None:
        raise RuntimeError("menu_version has no row: ensure_menu_version runs at start")
    env = new_envelope(
        "Heartbeat",
        order_id=None,
        branch_id=None,
        clock=clock,
        payload={"epoch": int(row[0]), "seq": int(row[1])},
    )
    enqueue(conn, MENU_EVENTS, env, key="heartbeat")


class HeartbeatSender:
    """Puts a heartbeat in the outbox at a fixed interval; the relay sends it. Each Inventory
    instance runs one: a second heartbeat a minute is harmless, a branch needs to hear one."""

    def __init__(
        self,
        connect: Callable[[], psycopg.Connection[Any]],
        clock: Clock,
        every_s: float = HEARTBEAT_EVERY_S,
    ) -> None:
        if every_s <= 0:
            raise ValueError("every_s must be positive")
        self._connect = connect
        self._clock = clock
        self._every_s = every_s

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                with self._connect() as conn:
                    emit_heartbeat(conn, self._clock)
            except psycopg.Error as exc:
                log.warning("heartbeat not queued: %s", exc)
            stop.wait(self._every_s)
