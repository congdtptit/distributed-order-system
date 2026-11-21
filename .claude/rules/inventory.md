---
paths:
  - "backend/inventory-service/**"
---

# Inventory

The `paths` above follow the module names in section 2 of `docs/03-implementation-plan.md`. If the layout changes in step 0, change `paths`.

## Read before editing

- `docs/01-business-spec.md`: BR1, BR6, BR11, BR12 in section 2; table 3.3 and the stock accounting part; section 3.4; the Inventory part of section 13.4.
- `docs/02-detailed-design.md`: section 3 (schema and the rules below it); the Inventory rows in section 6.

## Rules

- Reserve all ingredients of an order or none. Use the savepoint of section 13.4 so that a shortage rolls back only the stock deductions, while the Failed record and the deduplication row are still written.
- The condition `available >= :q AND NOT needs_check` sits inside the `UPDATE stock` statement. Do not check the flag with a separate read.
- Release, consume and waste run only when `UPDATE inventory_orders ... WHERE status = 'DANG_GIU'` changes exactly one row.
- Release the quantity recorded in `inventory_reservations`. Do not recompute it from the current recipe.
- A release command or a consumed report for an order with no record, or with a `THAT_BAI` record: do not touch `stock`, write an `alerts` row of kind `LENH_KHONG_KHOP`.
- Lock order: the order's `inventory_orders` row, the `stock` rows by ascending `ingredient_id`, the `dish_status` rows by ascending `dish_id`, and `menu_version` last.
- Computing dish status: lock the affected `dish_status` rows first, then read stock.
- Versions come from `UPDATE menu_version SET seq = seq + 1 RETURNING epoch, seq`. Do not use a SEQUENCE, a counter in RAM or the system clock.
- `origin_branch` is taken from the topic name `order-events.<branch>`.
- Returning the stored result goes only to the origin branch's `status-events` topic, never again to `kitchen-orders`.
- Do not delete any row of `inventory_orders` or `processed_events`.

## After every test

Run the two invariant queries of section 3 of document 02: `stock.reserved` equals the sum of the lines still held, and every line still held belongs to an order in `DANG_GIU`.

## Scenarios of this module

Steps 2 and 3 in section 7 of document 02: 5, 6, 9, 15, 16, 22, 24, 30, 39, 42, 43, 44, 48, 49. Phase 2: 18 and the Inventory part of 20.
