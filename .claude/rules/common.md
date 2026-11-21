---
paths:
  - "backend/common/**"
---

# Shared module: message envelope, outbox, consumer, dlq

The `paths` above follow the module names in section 2 of `docs/03-implementation-plan.md`. If the layout changes in step 0, change `paths`.

## Read before editing

- `docs/01-business-spec.md`: section 9 (common message envelope, table for bad messages), section 13.1 (topics and mandatory configuration), section 13.3 (the five consumer steps).
- `docs/02-detailed-design.md`: section 2 (the 13 event types and the notes below the table); the `processed_events`, `outbox_events` and `alerts` tables in section 3.

## Rules

- The consumer turns auto-commit off and follows the five steps of section 13.3 exactly: open a transaction, insert `event_id` into `processed_events`, apply the state table, write the outbox and commit, and only then commit the offset.
- A message whose `event_id` was already processed is skipped and nothing is emitted. Do not deduplicate on the pair of order id and message type.
- The handler is separate from the consumer loop: it receives one message and one DB transaction, and knows nothing about Kafka.
- An outbox row is marked as sent only after Kafka acknowledges it. The producer uses `acks=all` and `enable.idempotence=true`.
- A message going to the dlq is sent directly, not through the outbox. Order: send to the dlq and wait for the acknowledgement, write an `alerts` row of kind `CAN_KIEM_TRA`, then commit the offset.
- A deciding service (Inventory, Kitchen) that meets an unknown `event_type` moves it to the dlq and does not skip it. A type that is in the catalogue but not meant for that service is skipped, not sent to the dlq.
- The sending branch is derived from the topic name, never from `branch_id` in the message body.
- Every log line carries `order_id`.
- Time is read through a replaceable clock, never straight from the system clock.

## Scenarios of this module

26, 29, 31 (step 1 in section 7 of document 02).
