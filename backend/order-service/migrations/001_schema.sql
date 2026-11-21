-- Branch DB schema (POS and Online).
-- Copied verbatim from docs/02-detailed-design.md section 5; processed_events is "same as the Inventory DB"
-- and copied from section 3.
-- Applied migrations are immutable: change the schema in a new numbered file.

CREATE TABLE orders (
  order_id      UUID PRIMARY KEY,
  branch_id     TEXT NOT NULL,                    -- this branch; carried to the Central Order Replica
  status        TEXT NOT NULL CHECK (status IN
    ('CHO_KHO','DA_GIU','HOAN_TAT','DA_HUY','THAT_BAI')),
  status_rank   SMALLINT NOT NULL DEFAULT 0,      -- 0, 1, 2 per section 3.1
  close_reason  TEXT,
  cancel_flag   TEXT NOT NULL DEFAULT 'KHONG'
    CHECK (cancel_flag IN ('KHONG','DANG_YEU_CAU','BEP_KHONG_NAU')),
  cancel_requested_at TIMESTAMPTZ,                -- to show how long the request has waited
  cancel_message      TEXT,                       -- "Cannot cancel: the kitchen has started cooking"
  items         JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL
);

CREATE TABLE outbox_events (                      -- send queue
  id        BIGSERIAL PRIMARY KEY,
  event_id  UUID NOT NULL UNIQUE,
  order_id  UUID NOT NULL REFERENCES orders,
  kind      TEXT NOT NULL CHECK (kind IN ('TAO_DON','HUY')),
  topic     TEXT NOT NULL,
  payload   JSONB NOT NULL,
  attempted BOOLEAN NOT NULL DEFAULT FALSE,       -- the "send attempted" flag (BR9)
  sent_at   TIMESTAMPTZ                           -- NULL: not yet acknowledged by Kafka
);

CREATE TABLE menu_cache (                         -- phase 2, Flow C
  dish_id TEXT PRIMARY KEY,
  status  TEXT NOT NULL CHECK (status IN ('CON','HET','AN')),
  epoch   INT NOT NULL,
  seq     BIGINT NOT NULL
);

CREATE TABLE menu_cache_meta (                    -- exactly one row
  id            BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
  epoch         INT NOT NULL,
  last_heard_at TIMESTAMPTZ                       -- most recent message or heartbeat
);

CREATE TABLE replication_heartbeat (              -- replicated with orders; gives "data as of"
  branch_id TEXT PRIMARY KEY,
  beat_at   TIMESTAMPTZ NOT NULL
);

CREATE TABLE processed_events (
  event_id     UUID PRIMARY KEY,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
