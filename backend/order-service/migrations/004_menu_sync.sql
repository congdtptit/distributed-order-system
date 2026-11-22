-- Flow C at the branch (phase 2, revision 19 of docs/02-detailed-design.md, "Flow C in
-- practice"): the greatest epoch heard in a message or a heartbeat, so that the menu sync
-- knows to fetch the snapshot; and the one row of menu_cache_meta, at epoch 0 before the
-- first snapshot (any epoch Inventory announces is then greater).
ALTER TABLE menu_cache_meta ADD COLUMN newest_epoch INT NOT NULL DEFAULT 0;

INSERT INTO menu_cache_meta (epoch) VALUES (0) ON CONFLICT (id) DO NOTHING;
