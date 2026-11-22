"""The stock-check flag (BR6) and the version counter that orders its messages.

Section 3 of docs/02-detailed-design.md: every time an ingredient's flag changes, the
transaction runs ``UPDATE menu_version SET seq = seq + 1 RETURNING epoch, seq`` and emits
``IngredientCheckChanged`` to ``menu-events``, keyed by the ingredient ID. ``menu_version`` is
locked last, after the order row and the stock rows.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

import psycopg

from common.clock import Clock
from common.envelope import new_envelope
from common.outbox import enqueue
from common.topics import MENU_EVENTS

FIRST_EPOCH = 1


def ensure_menu_version(conn: psycopg.Connection[Any]) -> None:
    """Create the single ``menu_version`` row (epoch 1, seq 0) if it does not exist yet."""
    conn.execute(
        "INSERT INTO menu_version (epoch, seq) VALUES (%s, 0) ON CONFLICT (id) DO NOTHING",
        (FIRST_EPOCH,),
    )


def next_version(conn: psycopg.Connection[Any]) -> tuple[int, int]:
    """Take the next (epoch, seq). Locks ``menu_version`` until the transaction ends, so the
    order of ``seq`` is the commit order (a SEQUENCE does not guarantee that)."""
    row = conn.execute("UPDATE menu_version SET seq = seq + 1 RETURNING epoch, seq").fetchone()
    if row is None:
        raise RuntimeError("menu_version has no row: ensure_menu_version runs at start")
    return int(row[0]), int(row[1])


def emit_check_changed(
    conn: psycopg.Connection[Any], ingredient_id: str, needs_check: bool, clock: Clock
) -> None:
    """Announce a flag change to the Kitchen. Call after all stock rows are written."""
    epoch, seq = next_version(conn)
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


class ClearResult(StrEnum):
    CLEARED = "cleared"
    NOT_FOUND = "not_found"
    BELOW_RESERVED = "below_reserved"


@dataclass(frozen=True)
class Cleared:
    result: ClearResult
    available: Decimal | None = None
    reserved: Decimal | None = None


def clear_check(
    conn: psycopg.Connection[Any],
    ingredient_id: str,
    counted_on_hand: Decimal | None,
    clock: Clock,
) -> Cleared:
    """``POST /ingredients/{id}/clear-check`` (section 6 of document 02), in the caller's
    transaction. ``counted_on_hand`` is the counted on-hand stock: available plus reserved, so
    ``available = counted_on_hand - reserved``; below the reserved quantity it is refused and
    nothing changes. The flag is cleared and announced only if it was set."""
    row = conn.execute(
        "SELECT needs_check, available, reserved FROM stock WHERE ingredient_id = %s FOR UPDATE",
        (ingredient_id,),
    ).fetchone()
    if row is None:
        return Cleared(ClearResult.NOT_FOUND)
    flagged, available, reserved = bool(row[0]), Decimal(row[1]), Decimal(row[2])
    if counted_on_hand is not None:
        if counted_on_hand < reserved:
            return Cleared(ClearResult.BELOW_RESERVED, available, reserved)
        available = counted_on_hand - reserved
    conn.execute(
        "UPDATE stock SET available = %s, needs_check = FALSE WHERE ingredient_id = %s",
        (available, ingredient_id),
    )
    # Flow C: the ingredient's dishes may return to Available (or, with a low count, become
    # Sold out). Imported here: dishes.py takes its versions from this module.
    from inventory_service.dishes import recompute_dishes

    recompute_dishes(conn, [ingredient_id], clock)
    if flagged:
        emit_check_changed(conn, ingredient_id, False, clock)
    return Cleared(ClearResult.CLEARED, available, reserved)
