-- Inventory DB schema.
-- Copied verbatim from docs/02-detailed-design.md section 3.
-- Applied migrations are immutable: change the schema in a new numbered file.

CREATE TABLE stock (
  ingredient_id TEXT PRIMARY KEY,
  unit          TEXT NOT NULL,
  available     NUMERIC(12,3) NOT NULL CHECK (available >= 0),           -- available stock
  reserved      NUMERIC(12,3) NOT NULL DEFAULT 0 CHECK (reserved >= 0),  -- reserved
  consumed      NUMERIC(12,3) NOT NULL DEFAULT 0,   -- consumed, cumulative
  wasted        NUMERIC(12,3) NOT NULL DEFAULT 0,   -- waste, cumulative
  needs_check   BOOLEAN NOT NULL DEFAULT FALSE      -- flagged for stock check (BR6)
);

CREATE TABLE recipes (
  dish_id       TEXT NOT NULL,
  ingredient_id TEXT NOT NULL REFERENCES stock,
  quantity      NUMERIC(12,3) NOT NULL CHECK (quantity > 0),
  PRIMARY KEY (dish_id, ingredient_id)
);

CREATE TABLE inventory_orders (                     -- BR12: one row per order ID
  order_id         UUID PRIMARY KEY,
  origin_branch    TEXT NOT NULL,                   -- taken from the topic name order-events.<branch>
  status           TEXT NOT NULL
    CHECK (status IN ('DANG_GIU','THAT_BAI','DA_TRA','DA_DUNG')),
  reason           TEXT,                            -- Failed reason or release reason
  order_created_at TIMESTAMPTZ,                     -- NULL if the order data is invalid
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE inventory_reservations (               -- quantity recorded at reservation time
  order_id      UUID NOT NULL REFERENCES inventory_orders,
  ingredient_id TEXT NOT NULL REFERENCES stock,
  quantity      NUMERIC(12,3) NOT NULL CHECK (quantity > 0),
  outcome       TEXT CHECK (outcome IN ('DA_HOAN','DA_DUNG','HAO_HUT')),  -- NULL: still held
  PRIMARY KEY (order_id, ingredient_id)
);

CREATE TABLE dish_status (
  dish_id TEXT PRIMARY KEY,
  status  TEXT NOT NULL CHECK (status IN ('CON','HET','AN')),
  epoch   INT NOT NULL,
  seq     BIGINT NOT NULL
);

CREATE TABLE menu_version (                         -- exactly one row
  id    BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
  epoch INT NOT NULL,
  seq   BIGINT NOT NULL
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
