-- Copied verbatim from docs/02-detailed-design.md section 3 (added in revision 8).
-- Applied migrations are immutable: change the schema in a new numbered file.

-- The ingredient's display name, from backend/seed/menu.json.
ALTER TABLE stock ADD COLUMN name TEXT NOT NULL DEFAULT '';
