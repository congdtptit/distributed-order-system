-- Central Order Replica: the two tables the branch DBs publish (02 section 5,
-- "Replication to the Central Order Replica"), with the same definitions so that
-- logical replication can apply rows from every branch.
-- Copied verbatim from docs/02-detailed-design.md section 5.
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

CREATE TABLE replication_heartbeat (              -- replicated with orders; gives "data as of"
  branch_id TEXT PRIMARY KEY,
  beat_at   TIMESTAMPTZ NOT NULL
);
