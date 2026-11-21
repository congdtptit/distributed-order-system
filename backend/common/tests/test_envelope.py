"""The message envelope (section 9 of docs/01-business-spec.md) and topic names (section 13.1)."""

import json
import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest

from common.clock import FixedClock
from common.envelope import (
    EVENT_TYPES,
    UnreadableMessage,
    decode,
    encode,
    new_envelope,
    uuid_or_none,
)
from common.kafka import consumer_config, producer_config
from common.topics import branch_from_topic

CLOCK = FixedClock(datetime(2026, 11, 20, 9, 15, tzinfo=UTC))


def _valid() -> dict[str, object]:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "CancelRequested",
        "schema_version": 1,
        "order_id": str(uuid.uuid4()),
        "branch_id": "POS01",
        "occurred_at": "2026-11-20T09:15:00Z",
        "causation_id": None,
        "payload": {"reason_code": "KHACH_DOI_Y"},
    }


def test_the_catalogue_has_thirteen_event_types() -> None:
    assert len(EVENT_TYPES) == 13


def test_encode_then_decode_gives_the_same_envelope() -> None:
    order_id = uuid.uuid4()
    cause = uuid.uuid4()
    env = new_envelope(
        "OrderReserved",
        order_id=order_id,
        branch_id="POS01",
        clock=CLOCK,
        payload={"origin_branch": "POS01"},
        causation_id=cause,
    )
    assert decode(encode(env)) == env
    wire = json.loads(encode(env))
    assert wire["occurred_at"] == "2026-11-20T09:15:00Z"
    assert set(wire) == {
        "event_id",
        "event_type",
        "schema_version",
        "order_id",
        "branch_id",
        "occurred_at",
        "causation_id",
        "payload",
    }


def test_each_new_envelope_gets_a_new_event_id() -> None:
    a = new_envelope("Heartbeat", order_id=None, branch_id=None, clock=CLOCK)
    b = new_envelope("Heartbeat", order_id=None, branch_id=None, clock=CLOCK)
    assert a.event_id != b.event_id


def test_new_envelope_refuses_a_type_outside_the_catalogue() -> None:
    with pytest.raises(ValueError):
        new_envelope("OrderTeleported", order_id=None, branch_id=None, clock=CLOCK)


def test_decode_accepts_added_fields_and_converts_time_to_utc() -> None:
    data = _valid() | {"trace": "x", "occurred_at": "2026-11-20T16:15:00+07:00"}
    env = decode(json.dumps(data).encode())
    assert env.occurred_at == datetime(2026, 11, 20, 9, 15, tzinfo=UTC)
    assert env.occurred_at.tzinfo == UTC


def test_decode_keeps_an_unknown_type_and_a_higher_version_for_the_consumer_to_judge() -> None:
    env = decode(json.dumps(_valid() | {"event_type": "X", "schema_version": 9}).encode())
    assert (env.event_type, env.schema_version) == ("X", 9)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        b"\xff\xfe",
        b"not json",
        b"[1, 2]",
        json.dumps({k: v for k, v in _valid().items() if k != "event_id"}).encode(),
        json.dumps(_valid() | {"event_id": None}).encode(),
        json.dumps(_valid() | {"event_id": "123"}).encode(),
        json.dumps(_valid() | {"order_id": 5}).encode(),
        json.dumps(_valid() | {"event_type": ""}).encode(),
        json.dumps(_valid() | {"schema_version": "1"}).encode(),
        json.dumps(_valid() | {"schema_version": True}).encode(),
        json.dumps(_valid() | {"schema_version": 0}).encode(),
        json.dumps(_valid() | {"occurred_at": "2026-11-20T09:15:00"}).encode(),
        json.dumps(_valid() | {"occurred_at": "yesterday"}).encode(),
        json.dumps(_valid() | {"payload": []}).encode(),
        json.dumps(_valid() | {"branch_id": 1}).encode(),
    ],
)
def test_decode_rejects_what_is_not_an_envelope(raw: bytes | None) -> None:
    with pytest.raises(UnreadableMessage):
        decode(raw)


def test_uuid_or_none_reads_a_kafka_key() -> None:
    order_id = uuid.uuid4()
    assert uuid_or_none(str(order_id).encode()) == order_id
    assert uuid_or_none(b"heartbeat") is None
    assert uuid_or_none(b"\xff") is None
    assert uuid_or_none(None) is None


@pytest.mark.parametrize(
    ("topic", "branch"),
    [
        ("order-events.POS01", "POS01"),
        ("cancel-events.ONLINE", "ONLINE"),
        ("status-events.POS02", "POS02"),
        ("kitchen-orders", None),
        ("menu-events", None),
        ("dlq", None),
        ("order-events.", None),
        ("other-events.POS01", None),
        ("test.order-events.POS01", None),
    ],
)
def test_the_sending_branch_comes_from_the_topic_name(topic: str, branch: str | None) -> None:
    assert branch_from_topic(topic) == branch


def test_kafka_clients_use_the_mandatory_settings() -> None:
    """Section 13.1 (producer) and section 13.3 (offset auto-commit off) of the specification."""
    producer = producer_config("kafka1:19092", "x")
    assert producer["acks"] == "all"
    assert producer["enable.idempotence"] is True
    consumer = consumer_config("kafka1:19092", "group", "x")
    assert consumer["enable.auto.commit"] is False


def test_fixed_clock_moves_only_when_told() -> None:
    clock = FixedClock(datetime(2026, 1, 1, 7, tzinfo=timezone(timedelta(hours=7))))
    assert clock.now() == datetime(2026, 1, 1, 0, tzinfo=UTC)
    clock.advance(timedelta(hours=4))
    assert clock.now() == datetime(2026, 1, 1, 4, tzinfo=UTC)
    with pytest.raises(ValueError):
        FixedClock(datetime(2026, 1, 1))
