"""The branch's replication heartbeat (section 5 of docs/02-detailed-design.md, "Replication to
the Central Order Replica").

Every few seconds the branch moves its one ``replication_heartbeat`` row to the database's
``now()``. The row is published to the Central Order Replica together with ``orders``, and
logical replication applies one branch's transactions in commit order, so when a ``beat_at``
has reached the central DB, every order change the branch committed before it has too. That
value is the branch's "data as of" time in the Management report (scenario 55).

The time is the branch database's clock, not the service's replaceable clock: "data as of" is a
wall-clock time, and the scenarios that move the service clock forward do not need it.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any, Final

import psycopg

log = logging.getLogger(__name__)

BEAT_EVERY_S: Final = 5.0

_UPSERT: Final = """
    INSERT INTO replication_heartbeat (branch_id, beat_at) VALUES (%s, now())
    ON CONFLICT (branch_id) DO UPDATE SET beat_at = EXCLUDED.beat_at
"""


def beat(conn: psycopg.Connection[Any], branch: str) -> None:
    """One beat, in the caller's transaction."""
    conn.execute(_UPSERT, (branch,))


class Heartbeat:
    def __init__(
        self,
        connect: Callable[[], psycopg.Connection[Any]],
        branch: str,
        every_s: float = BEAT_EVERY_S,
    ) -> None:
        if every_s <= 0:
            raise ValueError("every_s must be positive")
        self._connect = connect
        self._branch = branch
        self._every_s = every_s

    def run(self, stop: threading.Event) -> None:
        """Beat until ``stop`` is set. A database that is down is retried on the next beat:
        meanwhile the central "data as of" simply stops moving, which is what it should show."""
        while not stop.is_set():
            try:
                with self._connect() as conn:
                    beat(conn, self._branch)
            except psycopg.Error as exc:
                log.warning("replication heartbeat not written: %s", exc)
            stop.wait(self._every_s)
