---
paths:
  - "order-service/**"
---

# Branch (POS and Online)

The `paths` above follow the module names in section 2 of `docs/03-implementation-plan.md`. If the layout changes in step 0, change `paths`.

## Read before editing

- `docs/01-business-spec.md`: BR3, BR5, BR9, BR10 in section 2; table 3.1 and the cancel flag; "Branch side" in section 6; "POS and Online side" in section 7; the branch rows in section 8.
- `docs/02-detailed-design.md`: section 5 (schema and the five conditional writes); the table on applying status messages at the end of section 2; the branch rows in section 6.

## Rules

- Use the five writes of section 5 of document 02 as they are. Do not rewrite them as "read, then write".
- The sender probes the connection to Kafka before setting the flag on an entry that has none. If the probe fails, it neither sets the flag nor sends.
- Set `attempted` and commit before calling Kafka. An entry with the flag is never cancelled locally and never dropped, even when sending reports an error.
- The cancel operation locks the `orders` row first, checks the terminal status and the cancel flag in the same transaction, and only then deletes the entry or inserts the cancel entry.
- The sender takes only the unsent row with the smallest `id` for each `order_id`. One failing entry does not block other orders.
- Apply status messages by rank, never "last message wins". A terminal status is never replaced.
- `CancelPending` applies only while the order is not terminal and the flag is `DANG_YEU_CAU`. `CancelRejected` turns the flag off and records the notice at any rank.
- The branch never decides a status by itself, except the local cancel of an order that was never attempted. A Kafka acknowledgement does not mean Inventory received the order.
- The dish cache merges dish by dish on `(epoch, seq)`. Do not assign a snapshot directly, and do not clear and reload.
- `POST /orders` does not check `menu_cache`; a Sold out dish is blocked only in the user interface while the data is fresh.

## Scenarios of this module

Step 6 in section 7 of document 02: 7, 10, 12, 36, 37, 53, 54. Phase 2: 19, 21 and the branch part of 20.
