---
paths:
  - "backend/kitchen-service/**"
---

# Kitchen

The `paths` above follow the module names in section 2 of `docs/03-implementation-plan.md`. If the layout changes in step 0, change `paths`.

## Read before editing

- `docs/01-business-spec.md`: BR2, BR7, BR8 in section 2; table 3.2 and the order of precedence right below it; section 5 (Flow A); the decision table in section 6; section 13.2; the Kitchen part of section 13.4.
- `docs/02-detailed-design.md`: section 4 (schema and the rules below it); the Kitchen rows in section 6.

## Rules

- One entry point: messages from `kitchen-orders`, messages from `cancel-events` and the three staff buttons all run the same code. It inserts a `CHUA_CO` row if none exists, runs `SELECT ... FOR UPDATE`, applies table 3.2, writes the outbox, then commits.
- Exactly one row per order id in `kitchen_orders`. Cancel-pending and the Failed result are values of the `status` column, not separate tables. Never delete a row.
- Never answer "Cancelled" for an order that has not arrived. A cancel request that arrives before the order only creates `HUY_CHO_DON` and emits `CancelPending`.
- The branch that sent a cancel request is taken from the topic name. `origin_branch` is written only from an Inventory message.
- `cancel_branches` holds every branch that requested cancellation; `cancel_reasons` holds the reason per branch, and a repeated request does not overwrite it.
- A cancel request from a branch other than the origin branch: keep the status, send no reply, write an `alerts` row of kind `HUY_SAI_CHI_NHANH`.
- A Failed message for an order with no record must be recorded as `THAT_BAI`, not ignored.
- The release command (`ReleaseRequested`) goes into the outbox in the same transaction as the `status` change, and each order gets one release command only.
- A ticket that is Cooking cannot be rejected. The three buttons return 409 when the ticket is no longer in the required status; that is the normal outcome of a race.
- `flagged_ingredients` is overwritten only when the message's `(epoch, seq)` is greater.
- On `menu-events` the Kitchen handles `IngredientCheckChanged` only; `DishStatusChanged` and `Heartbeat` are skipped, not sent to the dlq.

## Scenarios of this module

Steps 4 and 5 in section 7 of document 02: 1, 2, 3, 4, 6, 8, 23, 25, 27, 28, 33, 34, 35, 48, 50, 51, 52.
