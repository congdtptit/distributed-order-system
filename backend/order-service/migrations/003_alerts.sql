-- Copied verbatim from docs/02-detailed-design.md section 5 (added in revision 14).
-- Applied migrations are immutable: change the schema in a new numbered file.

-- Flow D: messages a person needs to look at. Same shape as the alerts table of Inventory and
-- the Kitchen (section 3), with one kind only: a message of the order was unreadable (moved to
-- the dlq) or of an unknown type (ignored), section 9 of the specification.
CREATE TABLE alerts (
  id               BIGSERIAL PRIMARY KEY,
  kind             TEXT NOT NULL CHECK (kind IN ('CAN_KIEM_TRA')),
  order_id         UUID,                            -- NULL if the order ID could not be read
  event_id         UUID,                            -- NULL if the message was unreadable
  source_topic     TEXT NOT NULL,                   -- the message that caused the alert
  source_partition INT NOT NULL,
  source_offset    BIGINT NOT NULL,
  detail           JSONB NOT NULL DEFAULT '{}',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (kind, source_topic, source_partition, source_offset)
);
