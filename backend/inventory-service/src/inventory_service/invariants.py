"""The stock-accounting invariants of section 3 of docs/02-detailed-design.md (and section 3.3
of the specification). Each query returns the offending rows; none means the invariant holds.

Used after every Inventory test, by ``scripts/check_invariants.py`` and by ``/invariants``.
"""

from typing import Any, LiteralString

import psycopg

CHECKS: list[tuple[str, LiteralString]] = [
    (
        "stock.reserved differs from the sum of lines still held",
        """
        SELECT s.ingredient_id, s.reserved,
               COALESCE(SUM(r.quantity) FILTER (WHERE r.outcome IS NULL), 0) AS held
          FROM stock s
          LEFT JOIN inventory_reservations r ON r.ingredient_id = s.ingredient_id
         GROUP BY s.ingredient_id, s.reserved
        HAVING s.reserved <> COALESCE(SUM(r.quantity) FILTER (WHERE r.outcome IS NULL), 0)
         ORDER BY s.ingredient_id
        """,
    ),
    (
        "a line still held belongs to an order that is not DANG_GIU",
        """
        SELECT r.order_id, r.ingredient_id, r.quantity, o.status
          FROM inventory_reservations r
          JOIN inventory_orders o ON o.order_id = r.order_id
         WHERE r.outcome IS NULL AND o.status <> 'DANG_GIU'
         ORDER BY r.order_id, r.ingredient_id
        """,
    ),
    (
        "negative stock quantity",
        """
        SELECT ingredient_id, available, reserved, consumed, wasted
          FROM stock
         WHERE available < 0 OR reserved < 0 OR consumed < 0 OR wasted < 0
         ORDER BY ingredient_id
        """,
    ),
]


def violations(conn: psycopg.Connection[Any]) -> dict[str, list[tuple[Any, ...]]]:
    """Title -> offending rows, for every check that found any."""
    found: dict[str, list[tuple[Any, ...]]] = {}
    for title, query in CHECKS:
        rows = conn.execute(query).fetchall()
        if rows:
            found[title] = rows
    return found
