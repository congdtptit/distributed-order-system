"""Rows of the ``alerts`` table of Inventory, the Kitchen and the branches (sections 3, 4 and
5 of docs/02-detailed-design.md): items of Flow D that a person needs to look at. A branch
writes only ``CAN_KIEM_TRA``.

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


def list_alerts(
    conn: psycopg.Connection[Any], kind: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    """The newest alerts first, of one kind if given: ``GET /alerts`` of Inventory and the
    Kitchen (section 6 of docs/02-detailed-design.md)."""
    cur = conn.execute(
        """
        SELECT id, kind, order_id, event_id, source_topic, source_partition, source_offset,
               detail, created_at
          FROM alerts
         WHERE %s::text IS NULL OR kind = %s
         ORDER BY id DESC
         LIMIT %s
        """,
        (kind, kind, limit),
    )
    names = [d.name for d in cur.description or []]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]
