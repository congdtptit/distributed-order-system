"""Check the stock-accounting invariants of the Inventory DB.

The two invariants come from section 3 of docs/02-detailed-design.md.
Exits 0 with a one-line summary when every check returns no rows; exits 1 and
prints the rows otherwise. Run inside the tools container:
    docker compose exec tools python scripts/check_invariants.py [DSN]
"""

import sys
from typing import LiteralString

import psycopg

DEFAULT_DSN = "postgresql://app:app@inventory-db:5432/inventory"

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


def main() -> int:
    dsn = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DSN
    failed = 0
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        for title, query in CHECKS:
            cur.execute(query)
            rows = cur.fetchall()
            if rows:
                failed += 1
                names = [d.name for d in cur.description or []]
                print(f"FAILED: {title} ({len(rows)} rows)")
                print("  " + " | ".join(names))
                for row in rows:
                    print("  " + " | ".join(str(v) for v in row))
    if failed:
        return 1
    print(f"Inventory invariants hold: {len(CHECKS)} checks, no offending rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
