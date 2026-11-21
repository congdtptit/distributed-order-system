"""Connect the branch DBs to the Central Order Replica with logical replication.

Runs once in compose (the ``replication-init`` container) after the branch services and the
Order Query Service have applied their migrations. It creates the publication at each branch
DB and one subscription per branch at the central DB, as at the end of section 5 of
docs/02-detailed-design.md. It can run any number of times.

Environment: CENTRAL_DSN, and BRANCH_DBS as ``<branch>=<host>`` pairs separated by commas,
for example ``POS01=pos01-db,POS02=pos02-db,ONLINE=online-db``. All branch DBs are named
``branch`` and share the user ``app``.
"""

import os
import sys

import psycopg
from psycopg import sql


def main() -> int:
    central_dsn = os.environ["CENTRAL_DSN"]
    pairs = [p.split("=", 1) for p in os.environ["BRANCH_DBS"].split(",") if p]
    for branch, host in pairs:
        branch_dsn = f"host={host} dbname=branch user=app password=app"
        with psycopg.connect(branch_dsn, autocommit=True) as conn:
            exists = conn.execute(
                "SELECT 1 FROM pg_publication WHERE pubname = 'central_pub'"
            ).fetchone()
            if exists is None:
                conn.execute(
                    "CREATE PUBLICATION central_pub FOR TABLE orders, replication_heartbeat"
                )
        subscription = f"sub_{branch.lower()}"
        with psycopg.connect(central_dsn, autocommit=True) as conn:
            exists = conn.execute(
                "SELECT 1 FROM pg_subscription WHERE subname = %s", (subscription,)
            ).fetchone()
            if exists is None:
                conn.execute(
                    sql.SQL("CREATE SUBSCRIPTION {} CONNECTION {} PUBLICATION central_pub").format(
                        sql.Identifier(subscription), sql.Literal(branch_dsn)
                    )
                )
        print(f"{branch}: {host} publishes to central-db as {subscription}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
