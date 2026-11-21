-- Copied verbatim from docs/02-detailed-design.md section 5 (added in revision 8).
-- Applied migrations are immutable: change the schema in a new numbered file.

-- The dish catalogue of this branch, loaded from backend/seed/menu.json on every start.
-- It serves the order form, also while the branch is offline (scenario 10).
CREATE TABLE dishes (
  dish_id TEXT PRIMARY KEY,
  name    TEXT NOT NULL
);
