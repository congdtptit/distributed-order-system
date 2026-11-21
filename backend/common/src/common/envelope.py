"""The common message envelope (section 9 of docs/01-business-spec.md) and the event catalogue
(section 2 of docs/02-detailed-design.md).

Fields may only be added to the envelope, never renamed or removed, so ``decode`` accepts and
ignores fields it does not know.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

from common.clock import Clock

SCHEMA_VERSION = 1
"""The highest ``schema_version`` this code understands."""

EVENT_TYPES: frozenset[str] = frozenset(
    {
        "OrderCreated",
        "CancelRequested",
        "OrderReserved",
        "OrderFailed",
        "StockConsumed",
        "ReleaseRequested",
        "CancelPending",
        "CancelRejected",
        "OrderCancelled",
        "OrderCompleted",
        "DishStatusChanged",
        "IngredientCheckChanged",
        "Heartbeat",
    }
)


class UnreadableMessage(ValueError):
    """The bytes are not an envelope: not JSON, or a field is missing or has the wrong type."""


@dataclass(frozen=True)
class Envelope:
    event_id: uuid.UUID
    event_type: str
    order_id: uuid.UUID | None
    branch_id: str | None
    occurred_at: datetime
    payload: dict[str, Any] = field(default_factory=lambda: {})
    causation_id: uuid.UUID | None = None
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "order_id": None if self.order_id is None else str(self.order_id),
            "branch_id": self.branch_id,
            "occurred_at": _format_time(self.occurred_at),
            "causation_id": None if self.causation_id is None else str(self.causation_id),
            "payload": self.payload,
        }


def new_envelope(
    event_type: str,
    *,
    order_id: uuid.UUID | None,
    branch_id: str | None,
    clock: Clock,
    payload: dict[str, Any] | None = None,
    causation_id: uuid.UUID | None = None,
) -> Envelope:
    """A new message with a new ``event_id`` (section 1 of document 02)."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"{event_type} is not in the event catalogue")
    return Envelope(
        event_id=uuid.uuid4(),
        event_type=event_type,
        order_id=order_id,
        branch_id=branch_id,
        occurred_at=clock.now(),
        payload={} if payload is None else payload,
        causation_id=causation_id,
    )


def encode(envelope: Envelope) -> bytes:
    return json.dumps(envelope.to_dict(), ensure_ascii=False, separators=(",", ":")).encode()


def decode(raw: bytes | None) -> Envelope:
    """Parse a message value. Raises UnreadableMessage; an unknown ``event_type`` or a higher
    ``schema_version`` is still a readable envelope and is judged by the consumer."""
    if raw is None:
        raise UnreadableMessage("the message has no value")
    try:
        data: object = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UnreadableMessage(f"not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise UnreadableMessage("the message is not a JSON object")
    obj = cast(dict[str, Any], data)

    event_type = _required(obj, "event_type")
    if not isinstance(event_type, str) or not event_type:
        raise UnreadableMessage("event_type must be a non-empty string")
    version = _required(obj, "schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise UnreadableMessage("schema_version must be a positive integer")
    branch_id = _required(obj, "branch_id")
    if branch_id is not None and not isinstance(branch_id, str):
        raise UnreadableMessage("branch_id must be a string or null")
    payload = _required(obj, "payload")
    if not isinstance(payload, dict):
        raise UnreadableMessage("payload must be a JSON object")

    event_id = _uuid(_required(obj, "event_id"), "event_id")
    if event_id is None:
        raise UnreadableMessage("event_id must not be null")
    return Envelope(
        event_id=event_id,
        event_type=event_type,
        schema_version=version,
        order_id=_uuid(_required(obj, "order_id"), "order_id"),
        branch_id=branch_id,
        occurred_at=_parse_time(_required(obj, "occurred_at")),
        causation_id=_uuid(obj.get("causation_id"), "causation_id"),
        payload=cast(dict[str, Any], payload),
    )


def uuid_or_none(value: str | bytes | None) -> uuid.UUID | None:
    """A UUID if ``value`` is one, else None. Used for the Kafka key of an unreadable message."""
    if value is None:
        return None
    try:
        return uuid.UUID(value.decode() if isinstance(value, bytes) else value)
    except (UnicodeDecodeError, ValueError):
        return None


def _required(obj: dict[str, Any], name: str) -> object:
    if name not in obj:
        raise UnreadableMessage(f"field {name} is missing")
    return obj[name]


def _uuid(value: object, name: str) -> uuid.UUID | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise UnreadableMessage(f"{name} must be a UUID string or null")
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise UnreadableMessage(f"{name} is not a UUID: {value!r}") from exc


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise UnreadableMessage("occurred_at must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise UnreadableMessage(f"occurred_at is not ISO 8601: {value!r}") from exc
    if parsed.tzinfo is None:
        raise UnreadableMessage("occurred_at must carry a timezone")
    return parsed.astimezone(UTC)


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
