"""Inventory receives the Kitchen's commands on ``stock-commands``: ``ReleaseRequested`` and
``StockConsumed``.

Table 3.3 of docs/01-business-spec.md (rows from Held, and the duplicate and unmatched rows),
BR6, BR12, Flow A step 5, the stock accounting table; the rules "Release, consumed, waste" and
"Unmatched command" in section 3 of docs/02-detailed-design.md.

Each command runs only when ``UPDATE inventory_orders ... WHERE status = 'DANG_GIU'`` changes
exactly one row. Then each line moves by the quantity recorded at reservation time (prohibition
6), never recomputed from the recipe. Lock order: the order row, the stock rows in ascending
``ingredient_id``, ``menu_version`` last.
"""

import logging
from decimal import Decimal
from typing import Any, cast

import psycopg

from common import reasons
from common.alerts import UNMATCHED_COMMAND, write_alert
from common.clock import Clock
from common.consumer import Handler, Incoming
from inventory_service.checks import emit_check_changed

log = logging.getLogger(__name__)

HELD, FAILED, RELEASED, CONSUMED = "DANG_GIU", "THAT_BAI", "DA_TRA", "DA_DUNG"
LINE_RELEASED, LINE_CONSUMED, LINE_WASTED = "DA_HOAN", "DA_DUNG", "HAO_HUT"


def make_release_handler(clock: Clock) -> Handler:
    def handle(conn: psycopg.Connection[Any], message: Incoming) -> None:
        env = message.envelope
        reason = env.payload.get("reason_code")
        # BR6: Inventory handles a release command according to its reason. Only the reason
        # "Spoiled ingredient" writes anything off; any other reason releases everything.
        spoiled = (
            _spoiled_ingredients(message) if reason == reasons.SPOILED_INGREDIENT else set[str]()
        )
        if not _leave_held(
            conn, message, RELEASED, reason if isinstance(reason, str) else None, clock
        ):
            return
        lines = _held_lines(conn, message)
        newly_flagged: list[str] = []
        for ingredient_id, q in lines:  # ascending ingredient_id
            if ingredient_id in spoiled:
                # Waste: out of reserved into wasted, and flag for stock check (BR6).
                was_flagged = conn.execute(
                    "SELECT needs_check FROM stock WHERE ingredient_id = %s FOR UPDATE",
                    (ingredient_id,),
                ).fetchone() == (True,)
                conn.execute(
                    "UPDATE stock SET reserved = reserved - %s, wasted = wasted + %s,"
                    " needs_check = TRUE WHERE ingredient_id = %s",
                    (q, q, ingredient_id),
                )
                _close_line(conn, message, ingredient_id, LINE_WASTED)
                if not was_flagged:
                    newly_flagged.append(ingredient_id)
            else:
                conn.execute(
                    "UPDATE stock SET available = available + %s, reserved = reserved - %s"
                    " WHERE ingredient_id = %s",
                    (q, q, ingredient_id),
                )
                _close_line(conn, message, ingredient_id, LINE_RELEASED)
        unknown = sorted(spoiled - {i for i, _ in lines})
        if unknown:
            log.warning(
                "order_id=%s event_id=%s spoiled ingredients not reserved for this order,"
                " ignored: %s",
                env.order_id,
                env.event_id,
                ", ".join(unknown),
            )
        for ingredient_id in newly_flagged:  # menu_version is locked last
            emit_check_changed(conn, ingredient_id, True, clock)
        log.info(
            "order_id=%s event_id=%s released; wasted and flagged: %s",
            env.order_id,
            env.event_id,
            ", ".join(sorted(spoiled & {i for i, _ in lines})) or "none",
        )

    return handle


def make_consumed_handler(clock: Clock) -> Handler:
    def handle(conn: psycopg.Connection[Any], message: Incoming) -> None:
        if not _leave_held(conn, message, CONSUMED, None, clock):
            return
        for ingredient_id, q in _held_lines(conn, message):
            # Out of reserved into consumed; available stock is not deducted again.
            conn.execute(
                "UPDATE stock SET reserved = reserved - %s, consumed = consumed + %s"
                " WHERE ingredient_id = %s",
                (q, q, ingredient_id),
            )
            _close_line(conn, message, ingredient_id, LINE_CONSUMED)
        log.info(
            "order_id=%s event_id=%s consumed", message.envelope.order_id, message.envelope.event_id
        )

    return handle


def _leave_held(
    conn: psycopg.Connection[Any],
    message: Incoming,
    to: str,
    reason: str | None,
    clock: Clock,
) -> bool:
    """Move the record from Held to ``to``. False when the record is not Held: a duplicate
    (Released, Consumed: ignored) or an unmatched command (no record, Failed: alert)."""
    env = message.envelope
    moved = conn.execute(
        "UPDATE inventory_orders SET status = %s, reason = COALESCE(%s, reason), updated_at = %s"
        " WHERE order_id = %s AND status = %s",
        (to, reason, clock.now(), env.order_id, HELD),
    ).rowcount
    if moved == 1:
        return True
    row = conn.execute(
        "SELECT status FROM inventory_orders WHERE order_id = %s", (env.order_id,)
    ).fetchone()
    status = None if row is None else str(row[0])
    if status in (RELEASED, CONSUMED):
        log.info(
            "order_id=%s event_id=%s %s ignored: the record is already %s",
            env.order_id,
            env.event_id,
            env.event_type,
            status,
        )
        return False
    # No record, or Failed: nothing to release or consume. Never add to stock (prohibition 8).
    source = message.source
    if source is None:
        raise ValueError("an unmatched command needs its Kafka position for the alerts row")
    write_alert(
        conn,
        UNMATCHED_COMMAND,
        order_id=env.order_id,
        event_id=env.event_id,
        source_topic=source.topic,
        source_partition=source.partition,
        source_offset=source.offset,
        detail={"event_type": env.event_type, "record_status": status},
    )
    log.warning(
        "order_id=%s event_id=%s unmatched %s: the record is %s; stock unchanged",
        env.order_id,
        env.event_id,
        env.event_type,
        status or "missing",
    )
    return False


def _held_lines(conn: psycopg.Connection[Any], message: Incoming) -> list[tuple[str, Decimal]]:
    """The lines still held, in ascending ``ingredient_id``, with their stock rows locked."""
    rows = conn.execute(
        """
        SELECT r.ingredient_id, r.quantity
          FROM inventory_reservations r
          JOIN stock s ON s.ingredient_id = r.ingredient_id
         WHERE r.order_id = %s AND r.outcome IS NULL
         ORDER BY r.ingredient_id
           FOR UPDATE OF s
        """,
        (message.envelope.order_id,),
    ).fetchall()
    return [(str(r[0]), Decimal(r[1])) for r in rows]


def _close_line(
    conn: psycopg.Connection[Any], message: Incoming, ingredient_id: str, outcome: str
) -> None:
    conn.execute(
        "UPDATE inventory_reservations SET outcome = %s"
        " WHERE order_id = %s AND ingredient_id = %s AND outcome IS NULL",
        (outcome, message.envelope.order_id, ingredient_id),
    )


def _spoiled_ingredients(message: Incoming) -> set[str]:
    """``spoiled_ingredients[]`` of ``ReleaseRequested``: ingredient IDs. Never raises: an
    exception would send the command to the dlq and leave the reservation held for good, so a
    malformed list is logged and what cannot be read is left out (the rest is released)."""
    env = message.envelope
    raw: object = env.payload.get("spoiled_ingredients", [])
    items = cast(list[object], raw) if isinstance(raw, list) else []
    spoiled = {i for i in items if isinstance(i, str)}
    if not isinstance(raw, list) or len(spoiled) != len(items):
        log.warning(
            "order_id=%s event_id=%s malformed spoiled_ingredients %s: only %s written off",
            env.order_id,
            env.event_id,
            repr(env.payload.get("spoiled_ingredients")),
            sorted(spoiled) or "nothing",
        )
    return spoiled
