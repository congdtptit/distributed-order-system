"""Rows of the ``alerts`` table of Inventory and the Kitchen (sections 3 and 4 of
docs/02-detailed-design.md): items of Flow D that a person needs to look at.

Every insert uses ON CONFLICT DO NOTHING on the unique key, so a Kafka redelivery of the same
message does not create a second row.
"""

import uuid
from typing import Any, Final

import psycopg
from psycopg.types.json import Jsonb

NEEDS_REVIEW: Final = "CAN_KIEM_TRA"
"""A message of the order went to the dlq: the order needs review."""
UNMATCHED_COMMAND: Final = "LENH_KHONG_KHOP"
WRONG_BRANCH_CANCEL: Final = "HUY_SAI_CHI_NHANH"


def write_alert(
    conn: psycopg.Connection[Any],
    kind: str,
    *,
    order_id: uuid.UUID | None,
    event_id: uuid.UUID | None,
    source_topic: str,
    source_partition: int,
    source_offset: int,
    detail: dict[str, Any] | None = None,
) -> bool:
    """Insert one alert; False if the same message already raised this kind of alert."""
    cur = conn.execute(
        """
        INSERT INTO alerts (kind, order_id, event_id, source_topic, source_partition,
                            source_offset, detail)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (kind, source_topic, source_partition, source_offset) DO NOTHING
        """,
        (
            kind,
            order_id,
            event_id,
            source_topic,
            source_partition,
            source_offset,
            Jsonb(detail or {}),
        ),
    )
    return cur.rowcount == 1
