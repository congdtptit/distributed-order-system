"""Check the stock-accounting invariants of the Inventory DB.

The checks are in inventory_service/invariants.py (section 3 of docs/02-detailed-design.md).
Exits 0 with a one-line summary when every check returns no rows; exits 1 and
prints the rows otherwise. Run inside the tools container:
    docker compose exec tools python scripts/check_invariants.py [DSN]
"""

import sys

import psycopg

from inventory_service.invariants import CHECKS

DEFAULT_DSN = "postgresql://app:app@inventory-db:5432/inventory"


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
