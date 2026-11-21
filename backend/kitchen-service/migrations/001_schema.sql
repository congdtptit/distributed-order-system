-- Kitchen DB schema.
-- Copied verbatim from docs/02-detailed-design.md section 4; alerts, processed_events and outbox_events
-- are "same as the Inventory DB" and copied from section 3.
-- Applied migrations are immutable: change the schema in a new numbered file.

CREATE TABLE kitchen_orders (
  order_id         UUID PRIMARY KEY,
  status           TEXT NOT NULL CHECK (status IN
    ('CHUA_CO','HUY_CHO_DON','CHO_NAU','DANG_NAU','HOAN_TAT','DA_HUY','THAT_BAI')),
  origin_branch    TEXT,                          -- origin branch, written only from the Inventory message
  cancel_branches  TEXT[] NOT NULL DEFAULT '{}',  -- every branch that has requested a cancel
  cancel_reasons   JSONB NOT NULL DEFAULT '{}',   -- reason per branch: {"POS01": "KHACH_DOI_Y"}
  cancelled_by     TEXT CHECK (cancelled_by IN ('CUSTOMER','KITCHEN')),
  close_reason     TEXT,                          -- Cancelled or Failed reason
  items            JSONB,                         -- dishes of the order, copied from OrderReserved
  reserved         JSONB,                         -- reserved ingredients, copied from OrderReserved
  spoiled          JSONB,                         -- ingredients reported spoiled on rejection
  order_created_at TIMESTAMPTZ,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE flagged_ingredients (                -- from IngredientCheckChanged
  ingredient_id TEXT PRIMARY KEY,
  needs_check   BOOLEAN NOT NULL,
  epoch         INT NOT NULL,
  seq           BIGINT NOT NULL
);

CREATE TABLE alerts (                               -- Flow D: items a person needs to look at
  id               BIGSERIAL PRIMARY KEY,
  kind             TEXT NOT NULL CHECK (kind IN
    ('CAN_KIEM_TRA','LENH_KHONG_KHOP','HUY_SAI_CHI_NHANH')),
  order_id         UUID,                            -- NULL if the order ID could not be read
  event_id         UUID,                            -- NULL if the message was unreadable
  source_topic     TEXT NOT NULL,                   -- the message that caused the alert
  source_partition INT NOT NULL,
  source_offset    BIGINT NOT NULL,
  detail           JSONB NOT NULL DEFAULT '{}',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (kind, source_topic, source_partition, source_offset)
);

CREATE TABLE processed_events (
  event_id     UUID PRIMARY KEY,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE outbox_events (
  id         BIGSERIAL PRIMARY KEY,
  event_id   UUID NOT NULL UNIQUE,
  topic      TEXT NOT NULL,
  msg_key    TEXT NOT NULL,
  payload    JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at    TIMESTAMPTZ                            -- NULL: not yet acknowledged by Kafka
);
