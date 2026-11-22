# Detailed design – Kafka events, DB schemas and API

Revision 14 · 22 Nov 2026 · @Naul · follows business specification v1.5

This document turns business specification v1.5 (the lean edition) into three things to code against: the Kafka event catalogue, each service's DB schema, and the API. There is no existing codebase to align with: the base flow is built in this project as well, so the event names, table names, column names and API paths here are the ones to use.

## Changes in revision 14

| Section | Change | Reason |
|---|---|---|
| 2, 5 | The branch DB gets an `alerts` table (migration `003`), kind `CAN_KIEM_TRA` only, written for a status message moved to the dlq and for one of unknown type; `GET /monitor` lists them. Every service now writes its alerts to its own table | Section 9 of the specification asks the branch to "raise an alert", but the branch DB had nowhere to keep one; a log line is lost on restart, cannot reach the screen and cannot be checked by query. Chosen by @Naul on 22 Nov 2026 |
| 5 | New rule "The branch in practice": the send states, the connectivity probe, the sender's backoff, one sender per branch, what `GET /monitor` lists, messages the branch cannot apply, the leftover cancel entry | Built in step 6 (22 Nov 2026); the spec review listed what the documents did not state |
| 5 | Note: the rank condition of write (4) never decides on its own | The step 6 mutation check: every write that makes an order terminal turns the flag off, and write (2) refuses a terminal order, so a terminal order with the flag `DANG_YEU_CAU` cannot exist. The condition stays as a guard |
| 6 | The branch API rows: `POST /orders` returns the order, invalid input is 400 (also for the cancel reason), the fields of `GET /monitor` | Built in step 6 |
| 6 | `GET /alerts` of Inventory and the Kitchen: newest first, at most 100, `kind` limited to that service's kinds (422 otherwise) | Built in step 6b, ahead of step 7, because the Kitchen screen shows these alerts |

## Changes in revision 13

| Section | Change | Reason |
|---|---|---|
| 4 | New rule "Cancel requests in practice": reasons, what a Cancel-pending record keeps, repeats, the answer to a Failed record with no origin, the alert detail | Built in step 5 (22 Nov 2026); the spec review listed what the documents did not state |
| 4 | Each message type is accepted only from its own topics; on a branch topic, Inventory's and the Kitchen's types count as unreadable | The handlers were chosen by `event_type` alone, so a misconfigured branch writing `OrderFailed` to its cancel topic could decide an order, or `ReleaseRequested` to its order topic could release stock; section 13.2 of the specification exists to stop exactly such configuration errors |
| 4 | The sentence on the requesting branch: it is added to `cancel_branches` only when the request is not ignored | The old wording read as if every request, wrong-branch ones included, joined the list |

## Changes in revision 12

| Section | Change | Reason |
|---|---|---|
| 2 | The Kitchen's stored result for a Completed record is `OrderCompleted` | The note named only Cancel-pending, Cancelled and Failed; built in step 4 |
| 4 | The staff buttons lock the existing row and do not insert a `CHUA_CO` row; no row means 404 | The rule said all three entry points insert the placeholder. A button acts on a ticket that already exists, and inserting rows for unknown order IDs would only leave junk; the spec review of step 4 found the mismatch |
| 4 | New rule "Tickets in practice": `OrderFailed` reaching a Queued or Cooking ticket, malformed messages from Inventory, the reason when a Cancel-pending record has none for the origin branch, the input rules of Reject, the answers of the buttons and of `GET /tickets` | Built in step 4; the spec review listed what the documents did not state |

## Changes in revision 11

| Section | Change | Reason |
|---|---|---|
| 3 | New rule "Release commands and Consumed reports in practice": only the Spoiled reason writes off; spoiled ingredients not reserved for the order; a malformed list; the `reason` column; one `IngredientCheckChanged` per newly flagged ingredient; the starting `menu_version` row | Built in step 3 (22 Nov 2026); the spec review listed what the documents did not state. Writing off by reason follows BR6 ("according to its reason") |
| 6 | The Inventory stock APIs: 404 for an unknown ingredient, 422 for invalid input, the 409 body, what the responses return, `clear-check` on an ingredient that is not flagged | Built in step 3 |

## Changes in revision 10

| Section | Change | Reason |
|---|---|---|
| 1 | The `reason_code` values of the catalogue in section 10 of the specification | The documents named the reasons but gave no codes; Inventory's `OrderFailed` needs them. @Naul chose English codes in upper case on 22 Nov 2026 |
| 3 | New rule "Receiving `OrderCreated`": the order of the checks, what counts as invalid order data, how the Failed reason is chosen, the limits on time and quantity, the message that cannot be recorded | Built in step 2 (22 Nov 2026); the specification lists the reasons but not their order or the exact data checks |
| 3 | The reservation locks the order's `stock` rows with `SELECT ... FOR UPDATE` before the conditional `UPDATE` | The spec review of step 2 found that reading the flag after a failed `UPDATE`, without a lock, could give the wrong reason |

## Changes in revision 9

| Section | Change | Reason |
|---|---|---|
| 2 | New note "The shared consumer": which errors count as transient, that handlers turn invalid order data into business results instead of raising, the dlq header names, Kafka client settings beyond section 13.1 of the specification, and that a message whose processing stopped part-way is read again | Built in step 1 (22 Nov 2026). The specification gives the categories of section 9 but not which errors fall in each; these choices are now fixed in code and tests |
| 2 | The skip rule for known types not meant for a service applies on every topic, not only on `menu-events` | The consumer looks handlers up by `event_type`; a known type on another topic is a configuration error, not an unknown message |
| 2 | Known limit: the attempt counter is kept in memory | A message that kills the process is redelivered after each restart and never reaches the dlq; the lean edition accepts this (section 15 of the specification) |
| 3 | `outbox_events.payload` holds the whole envelope; the relay holds the row locks while it waits for Kafka; one instance can also send rows out of order | Built in step 1; the schema did not say what `payload` holds |

## Changes in revision 8

| Section | Change | Reason |
|---|---|---|
| 1 | The dish catalogue and the seed data come from one file, `backend/seed/menu.json` | No document said where dish names, ingredient names, recipes and starting stock come from; the order form had no source of dishes in phase 1, since `GET /menu` is phase 2. Decided by @Naul on 22 Nov 2026 |
| 2 | `items[]` of `OrderCreated` and `OrderReserved` carry the dish name; `reserved[]` carries the ingredient name and unit | The Kitchen screen shows names without calling another service, and an order keeps the names it was placed with |
| 3 | `stock.name` | Ingredient names for the screens |
| 5, 6 | The branch's `dishes` table and `GET /dishes`; `POST /orders` rejects a dish that is not in it | The order form works while the branch is offline (scenario 10) |

## Changes in revision 7

| Section | Change | Reason |
|---|---|---|
| 9 | The replication row points to section 2 of document 03 instead of naming a compose file | The compose setup was split into several files on 22 Nov 2026 |

## Changes in revision 6

| Section | Change | Reason |
|---|---|---|
| 5, 9 | Logical replication to the Central Order Replica was trial-run; the result is in section 9 | Risk 2 in section 6 of document 03, assigned to step 0 |
| 6 | The screens' module is named `frontend` | The repository was split into `backend/` and `frontend/` (section 2 of document 03) |

## Changes in revision 5

| Section | Change | Reason |
|---|---|---|
| 6 | States that the screens are a client of these APIs, not a service, and that each service publishes its OpenAPI document | A TypeScript frontend was added on 21 Nov 2026 (section 2 of document 03); its types are generated from that document |
| 8 | The note on the specification's open points: three of the five are confirmed | Confirmed by @Naul on 21 Nov 2026 |

## Changes in revision 4

Revision 4 follows two decisions of 21 Nov 2026: the project is built from scratch, with no B5 baseline, and it is written in Python. The language does not change this document; the missing baseline does, because Management reporting now has to be designed here.

| Section | Change | Reason |
|---|---|---|
| Introduction, 8 | Removed the dependency on a B5 baseline; point 1 is marked as no longer applying | There is no B5 codebase, so there are no existing names to defer to |
| 5, 6, 7 | Added `branch_id` on `orders`, the `replication_heartbeat` table, the replication set-up and `GET /reports/summary`; step 7 now builds them | The earlier revisions kept "the base flow's Order Query Service", which does not exist |
| 8 | New point 12 on replication and reporting; agreed later the same day | It is a design choice the specification leaves open |
| 9 | Recorded the re-run after the DDL change in section 5 | The trial-run script reads the DDL from this document |

## Changes in revision 3

Revision 3 brings the changes of specification v1.5 into the design. The most significant change is the rule on when the sender starts a send attempt, which was missing from both specification v1.4 and revision 2.

| Section | Change | Reason |
|---|---|---|
| 5, 8 | Added the rule on starting a send attempt: for an entry without the flag, the sender sets the flag and sends only when a connectivity probe to Kafka has just succeeded (point 11 in section 8) | BR9 of specification v1.5. Without this rule an order created while offline still gets flagged, and scenario 10 fails |
| 3 | A release command or a Consumed report that reaches a Failed record also writes an `alerts` row of kind `LENH_KHONG_KHOP` | Table 3.3 of specification v1.5 |
| 6 | Added `GET /monitor` at Inventory and the Kitchen for the slow-consumer warning; `GET /stock` also serves the list of ingredients awaiting a stock check | The four new rows in Flow D of specification v1.5 |
| 7 | Placed the 8 new scenarios (48–55) into the steps and added step 7 for reporting; phase 1 now has 40 scenarios | Section 12 of specification v1.5 |
| Top of file | Dropped "v1.4" from the title and the file name; the first line states the specification version this design follows. On 21 Nov 2026 the documents were translated into English and this file was renamed to `02-detailed-design.md` | The number in the old title was the specification's version, not this document's |

## Changes in revision 2

Revision 2 fixes four defects found when checking the first version against the specification and clarifies seven points that were left open. The first four rows are defects; the remaining rows are clarifications.

| Section | Change | Reason |
|---|---|---|
| 3, 4, 6 | Added the `alerts` table at Inventory and the Kitchen, and added `GET /alerts` | Scenario 29 requires marking an order as "needs review", but the schema had nowhere to store that. Scenarios 22, 27 and 34 can now be checked with a query |
| 2, 5 | Added operation (4) for `CancelPending`, conditional on rank and flag; added operation (5) for `CancelRejected` | Messages from Inventory and messages from the Kitchen do not reach the branch in order. Without the condition, an order that is already Failed gets its cancel flag turned back on (scenario 8) |
| 5, 6 | Cancel operation (2) locks the `orders` row first, and only then checks and deletes the entry | Pressing cancel twice in quick succession made an order that was never sent still emit a cancel entry (scenario 10) |
| 7 | `IngredientCheckChanged`, `flagged_ingredients` and `menu_version` moved up to phase 1 | The specification moves only the "dish becomes Sold out" part of scenario 6 to phase 2; the ticket-warning part belongs to phase 1 |
| 3 | Lock the `dish_status` rows before computing dish status; spelled out Inventory's lock order | `menu_version` serializes only the assignment of `seq`, not the computation |
| 3, 6 | Added the `epoch` bump procedure and its API | Scenario 20 needs this operation; without it the snapshot still carries the old generation |
| 6 | `clear-check` takes the counted on-hand stock, not the available stock | The person doing the stock check also counts the reserved part |
| 4 | `cancel_reason` became `cancel_reasons`, storing the reason per branch | A wrong-branch request that arrives first must not overwrite the origin branch's reason |
| 2, 3 | Inventory takes `origin_branch` from the topic name; spelled out the two deduplication layers and how Inventory returns the stored result | The first version covered only the Kitchen side |
| 2 | Messages going to the dlq are sent directly, not through the outbox; the Kitchen ignores `DishStatusChanged` and `Heartbeat` | A broken message may not be JSON; the other two are known types and must not go to the dlq |
| 7, 8 | Spelled out the test level of each step; added four points to confirm (7–10); removed the stand-alone "agreed" line at the end of section 8 | That line did not say which point it applied to; the confirmation status is now recorded at the top of section 8 |

The statements in sections 3, 4 and 5 have been trial-run on PostgreSQL; the results are in section 9.

## 1. Scope and conventions

Specification v1.5 is the deciding source for business behaviour. When this document differs from the specification, the specification is right and this document must be fixed.

- **Order ID (`order_id`)**: a UUID generated by the branch when the order is created, used as the Kafka partition key and as the primary key in all three places (branch, Inventory, the Kitchen).
- **Event ID (`event_id`)**: a UUID generated by the emitting side at the moment it writes the outbox. Resending the same outbox row keeps the same `event_id`; creating a new message, including one that returns the stored result, generates a new `event_id`.
- **Branch ID (`branch_id`)**: `POS01` … `POSN` and `ONLINE`. Per-branch topic names have the form `order-events.POS01`.
- **Time**: UTC, ISO 8601 format. The order's `created_at` is written by the branch and does not change across messages; Inventory uses it to check the X-hour limit (BR11).
- **Statuses in the DB**: unaccented upper-case codes (`CHO_KHO`, `DANG_GIU`…), continuing the naming of `CHUA_CO` and `THAT_BAI` in section 13.4 of the specification.
- **Reasons**: fixed codes from the catalogue in section 10 of the specification; no free text. The codes are English in upper case (chosen by @Naul on 22 Nov 2026), unlike the status codes; the screens show the Vietnamese wording. They are defined once in `backend/common/src/common/reasons.py`:

  | Group | Reason in section 10 | `reason_code` |
  |---|---|---|
  | Failed (Inventory) | Insufficient ingredients | `INSUFFICIENT_INGREDIENTS` |
  | Failed (Inventory) | Ingredient awaiting stock check | `AWAITING_STOCK_CHECK` |
  | Failed (Inventory) | Dish has no recipe | `NO_RECIPE` |
  | Failed (Inventory) | Order expired | `ORDER_EXPIRED` |
  | Failed (Inventory) | Invalid creation time (in the future) | `FUTURE_CREATION_TIME` |
  | Failed (Inventory) | Invalid order data | `INVALID_ORDER_DATA` |
  | Kitchen rejection | Equipment failure | `EQUIPMENT_FAILURE` |
  | Kitchen rejection | Short-staffed | `SHORT_STAFFED` |
  | Kitchen rejection | Spoiled ingredient | `SPOILED_INGREDIENT` |
  | Customer cancel (proposed) | Customer changed their mind | `CHANGED_MIND` |
  | Customer cancel (proposed) | Customer waited too long | `WAITED_TOO_LONG` |
  | Customer cancel (proposed) | Cashier entered the wrong order | `WRONG_ORDER_ENTERED` |
- **Ingredient quantities**: decimal numbers with a fixed unit per ingredient, type `NUMERIC(12,3)`.
- **Catalogue and seed data**: dishes (id, Vietnamese name), ingredients (id, name, unit, starting stock) and recipes come from one file, `backend/seed/menu.json`. Each branch loads the dishes into its own `dishes` table on every start (insert or update). Inventory loads ingredients, stock and recipes on its first start only, when `stock` is empty, so that a restart never overwrites stock that has changed. Ids are unaccented upper-case codes like the status codes (`PHO_BO`, `THIT_BO`). There are no prices: payment is out of scope (section 11 of the specification).

## 2. Kafka event catalogue

The system has 13 event types across 6 topic groups, not counting the dlq. Every event uses the common message envelope in section 9 of the specification; the table below gives only the `payload` part.

```json
{ "event_id": "uuid", "event_type": "CancelRequested", "schema_version": 1,
  "order_id": "uuid", "branch_id": "POS01", "occurred_at": "2026-11-20T09:15:00Z",
  "causation_id": "event_id of the message that caused this one", "payload": { } }
```

| event_type | Topic | Sender → receiver | payload | Emitted when |
|---|---|---|---|---|
| `OrderCreated` | `order-events.<branch>` | Branch → Inventory | `created_at`, `channel` (POS, ONLINE), `items[{dish_id, name, quantity}]` | A cashier or customer submits a valid order |
| `CancelRequested` | `cancel-events.<branch>` | Branch → Kitchen | `reason_code` | An order is cancelled whose create-order entry already has the "send attempted" flag (BR9) |
| `OrderReserved` | `kitchen-orders` | Inventory → Kitchen | `origin_branch`, `created_at`, `items[]`, `reserved[{ingredient_id, name, unit, quantity}]` | Inventory reserves all the ingredients |
| `OrderReserved` | `status-events.<branch>` | Inventory → origin branch | empty | Same transaction as the row above; the branch moves to Reserved |
| `OrderFailed` | `kitchen-orders` and `status-events.<branch>` | Inventory → Kitchen, origin branch | `origin_branch`, `reason_code` | Inventory rejects the order (section 10 of the specification) |
| `StockConsumed` | `stock-commands` | Kitchen → Inventory | empty | Staff press Start cooking |
| `ReleaseRequested` | `stock-commands` | Kitchen → Inventory | `cancelled_by` (CUSTOMER, KITCHEN), `reason_code`, `spoiled_ingredients[]` | The Kitchen confirms a cancellation or rejects a ticket (the release command) |
| `CancelPending` | `status-events.<branch>` | Kitchen → requesting branch | empty | The Kitchen creates, or already has, a Cancel-pending record: "kitchen will not cook" |
| `CancelRejected` | `status-events.<branch>` | Kitchen → origin branch | `kitchen_status` (DANG_NAU, HOAN_TAT) | A cancel request arrives when the ticket is already Cooking or Completed |
| `OrderCancelled` | `status-events.<branch>` | Kitchen → origin branch | `cancelled_by`, `reason_code` | The Kitchen confirms a cancellation or rejects a ticket |
| `OrderCompleted` | `status-events.<branch>` | Kitchen → origin branch | empty | Staff press Complete |
| `DishStatusChanged` | `menu-events` | Inventory → all branches | `dish_id`, `status` (CON, HET, AN), `epoch`, `seq` | A dish changes between Available, Sold out and Hidden (BR10) |
| `IngredientCheckChanged` | `menu-events` | Inventory → Kitchen | `ingredient_id`, `needs_check`, `epoch`, `seq` | An ingredient is flagged for stock check, or the flag is cleared |
| `Heartbeat` | `menu-events` | Inventory → all branches | current `epoch`, `seq` | Every 60 seconds |

Notes on the table:

- `OrderReserved` and `OrderFailed` going to two topics are two outbox rows with two different `event_id` values, written in the same Inventory transaction.
- "Return the stored result" means re-emitting the event type that matches the stored status, with a new `event_id`. The Kitchen emits `CancelPending` when at Cancel-pending, `OrderCancelled` when at Cancelled, `OrderFailed` when at Failed, with `reason_code` taken from `close_reason`, and `OrderCompleted` when at Completed. How Inventory returns the stored result is described in section 3. Receivers already tolerate duplicate messages thanks to the rank rule (section 3.1 of the specification) and BR12.
- **Names travel with the order.** The branch copies each dish's name from its `dishes` table into `items[]` of `OrderCreated`; Inventory passes `items[]` on and copies each ingredient's `name` and `unit` from `stock` into `reserved[]` of `OrderReserved`. Names are for display only: no rule reads them, and an order keeps the names it was placed with.
- A cancel request from a branch other than the origin branch gets no reply message; the Kitchen writes an `alerts` row of kind `HUY_SAI_CHI_NHANH` (section 13.2 of the specification).
- Messages on `menu-events` belong to no order: `order_id` is `null`, the partition key is `dish_id` or `ingredient_id`, and `Heartbeat` alone uses the fixed key `heartbeat`.
- Each side handles only the message types meant for it on `menu-events`: the Kitchen handles `IngredientCheckChanged`, and branches handle `DishStatusChanged` and `Heartbeat`. The other types in this catalogue are known types: the receiver ignores them, does not write `processed_events` and does not move them to the dlq. The same holds on every topic: a known type that a service has no handler for is skipped this way (revision 9).
- A message going to the dlq keeps its original key and content and gains headers: `original_topic`, `original_partition`, `original_offset`, `consumer`, `error`. The consumer sends this message straight to the dlq, not through the outbox, because the content may not be JSON. The order is: send to the dlq and wait for Kafka's acknowledgement, write an `alerts` row of kind `CAN_KIEM_TRA`, and only then commit the offset.
- **The shared consumer** (`backend/common`, built in step 1) applies the five steps of section 13.3 of the specification and the table in its section 9 as follows:
  - *Transient error*: a PostgreSQL `OperationalError` (lost connection, timeout, deadlock, serialization failure, lock timeout). Retried without limit with growing backoff, not counted as an attempt.
  - *Permanent error*: any other exception, an unreadable message included. Tried 5 times (section 10 of the specification), each time in a new transaction that is rolled back, then moved to the dlq. A handler therefore never raises for invalid order data: it records the business result itself (BR12, scenario 39), and an exception means a bug.
  - *Unknown `event_type` or higher `schema_version`*: on the deciding side, moved to the dlq at once, without the 5 attempts.
  - *Interrupted processing*: if a message's steps stop part-way on a Kafka error (the dlq send, the offset commit), the consumer moves its read position back to that message; if the DB commit had happened, step 2 blocks the repeat. The attempt counter lives in memory, so a message that kills the process is retried after every restart and never reaches the dlq (known limit).
  - *Client settings* beyond section 13.1: consumer `auto.offset.reset=earliest`, `session.timeout.ms=10000` (a stopped instance's partitions move after 10 s), `topic.metadata.refresh.interval.ms=30000` (a new branch topic is seen within 30 s); producer `message.timeout.ms=30000` (after that a send counts as failed and the outbox row stays unsent).
  - *Alerts*: every service writes its "raise an alert" as an `alerts` row in its own DB, plus an error log line. The branch's table (section 5, revision 14) has one kind, `CAN_KIEM_TRA`, written both for a message moved to the dlq and for an unknown type it ignores; `detail.error` tells them apart.

The branch applies status messages as follows:

| Event received | Order at the branch | "Cancel requested" flag |
|---|---|---|
| `OrderReserved` | Reserved (rank 1) | Unchanged |
| `OrderFailed` | Failed (rank 2) | Off |
| `OrderCancelled` | Cancelled (rank 2) | Off |
| `OrderCompleted` | Completed (rank 2) | Off |
| `CancelPending` | Unchanged | Adds the line "kitchen will not cook", only when the order is not in a terminal status and the flag is `DANG_YEU_CAU`; otherwise ignored |
| `CancelRejected` | Unchanged | Off, and shows "Cannot cancel: the kitchen has started cooking", even when the order is already in a terminal status |

The condition on the `CancelPending` row is mandatory. `OrderFailed` emitted by Inventory and `CancelPending` emitted by the Kitchen travel through two different outbox relays, so `CancelPending` can arrive after the order is already Failed. `CancelRejected` needs no rank condition: the Kitchen emits it only when the ticket is already Cooking or Completed, and in the Completed case it always arrives after `OrderCompleted`.

## 3. Inventory DB schema

Inventory needs nine tables: stock, recipes, order records, per-line reservations, dish status, the version counter, alerts, deduplication and the outbox.

```sql
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
```

Added in revision 8, as migration `002`:

```sql
-- The ingredient's display name, from backend/seed/menu.json.
ALTER TABLE stock ADD COLUMN name TEXT NOT NULL DEFAULT '';
```

Rules that go with the schema:

- **Origin branch**: `origin_branch` is taken from the name of the topic the `OrderCreated` message arrived on, not from `branch_id` in the message (section 9 of the specification).
- **Two deduplication layers**: with the same `event_id`, `processed_events` blocks the message and Inventory emits nothing (section 13.3 of the specification). With a different `event_id` but the same `order_id`, `INSERT INTO inventory_orders ... ON CONFLICT (order_id) DO NOTHING` inserts no row, and Inventory returns the stored result without re-evaluating the order (BR12).
- **Inventory returns the stored result**: it emits only to `status-events.<branch>` of the origin branch, not again to `kitchen-orders`, because the Kitchen already received the original message through the outbox. A `THAT_BAI` record emits `OrderFailed` with the stored reason; a `DANG_GIU`, `DA_TRA` or `DA_DUNG` record emits `OrderReserved`.
- **Reserve**: exactly as in the SQL in section 13.4 of the specification. The `UPDATE stock` statement subtracts from `available` and adds to `reserved`, under the condition `available >= :q AND NOT needs_check`; each reserved ingredient gets one `inventory_reservations` row. The demand of the whole order is summed per ingredient first, so each ingredient has only one `UPDATE` statement.
- **Receiving `OrderCreated`** (built in step 2):
  - *Order of the checks*: (1) the order ID already has a record: return the stored result; (2) invalid order data; (3) created more than X hours ago, then created after now plus the tolerance; (4) a dish with no recipe; (5) the stock. Invalid data comes before the time limit because the limit needs a readable creation time. The first check that fails gives the reason.
  - *Invalid order data* (`INVALID_ORDER_DATA`): `created_at` missing or not an ISO 8601 time with a time zone; `channel` not `POS` or `ONLINE`; `items` missing, not a list or empty; an item that is not an object, whose `dish_id` is not a non-empty string, whose `quantity` is not a whole number above 0 (`1.5`, `"1"` and `true` are invalid), or whose `name` is present but not a string. `name` itself may be missing: it is for display only. The same dish on two lines is summed. The record keeps `order_created_at` NULL.
  - *Time limit*: X and the tolerance come from the service's environment (`ORDER_EXPIRY_HOURS`, default 4; `FUTURE_TOLERANCE_MINUTES`, default 5) until section 10 of the specification is confirmed. An order created exactly X hours ago, or exactly at now plus the tolerance, is accepted.
  - *Reason when the stock decides*: the transaction locks the order's `stock` rows in ascending `ingredient_id` with `SELECT ... FOR UPDATE` and decides from them: if any ingredient is flagged for stock check the reason is `AWAITING_STOCK_CHECK`, even when another one is also short (BR6); otherwise, if any is short, `INSUFFICIENT_INGREDIENTS`. Only then does it run the `UPDATE` of section 13.4, condition included, which therefore always deducts and stays as a safeguard. A demand larger than `NUMERIC(12,3)` can hold counts as short.
  - *What is forwarded*: `OrderReserved` on `kitchen-orders` carries `created_at` and `items[]` exactly as received, and `reserved[]` in ascending `ingredient_id` with `quantity` as a JSON number. The quantities are for display; releases always use `inventory_reservations` (prohibition 6). Every reply carries the origin branch as `branch_id` and the incoming `event_id` as `causation_id`.
  - *Returning the stored result* goes to the stored `origin_branch`, whatever topic the resend came on.
  - *A message that cannot be recorded*: an `OrderCreated` without `order_id`, or one on a topic that names no branch, cannot get a record keyed by order ID. It counts as unreadable: 5 attempts, then the dlq (section 2, "The shared consumer").
- **Release, consumed, waste**: these run only when `UPDATE inventory_orders SET status = ... WHERE order_id = :id AND status = 'DANG_GIU'` changes exactly one row. If no row changes, it is a duplicate message or an unmatched command: do not touch `stock`.
- **Unmatched command**: a release command or a Consumed report for an order with no record, or for an order whose record is `THAT_BAI`, writes an `alerts` row of kind `LENH_KHONG_KHOP`, along with a log line containing `order_id` and `event_id`. A command that reaches a `DA_TRA` or `DA_DUNG` record is a duplicate message: ignore it and write no alert.
- **Release commands and Consumed reports in practice** (built in step 3):
  - Only a release whose `reason_code` is `SPOILED_INGREDIENT` writes anything off (BR6: "according to its reason"). Any other reason releases every line, even if `spoiled_ingredients[]` is not empty.
  - A spoiled ingredient that was not reserved for the order is ignored with a log line: nothing to write off, no flag. A malformed `spoiled_ingredients` (not a list of IDs) is logged and whatever cannot be read is left out; the handler does not raise, because the command would go to the dlq and the reservation would stay held for good. A missing list means none.
  - Writing off an ingredient that is already flagged adds to `wasted` but sends no second `IngredientCheckChanged`. Several newly flagged ingredients each get their own message and `seq`, in ascending `ingredient_id`, in the same transaction. `IngredientCheckChanged` has no `causation_id` and no `branch_id`.
  - The `reason` column takes the release's `reason_code`; Consumed leaves it as it was. `cancelled_by` is not stored at Inventory.
  - The `alerts` row of an unmatched command has `detail = {event_type, record_status}`, where `record_status` is null when there is no record.
  - `menu_version` starts at `epoch = 1, seq = 0`. Inventory inserts that row on start if it is missing, so the first flag change has `seq = 1`.
- **The `alerts` table**: Inventory uses two kinds, `CAN_KIEM_TRA` (a message of the order went to the dlq) and `LENH_KHONG_KHOP`. Every insert uses `ON CONFLICT DO NOTHING` on the unique key, so a Kafka redelivery does not create a second row. For an unreadable message, `order_id` is taken from the message's Kafka key if the key is a UUID.
- **Lock order**: every Inventory transaction locks in exactly this order: the order's `inventory_orders` row, the `stock` rows in ascending `ingredient_id`, the `dish_status` rows in ascending `dish_id`, and finally the `menu_version` row. No transaction locks in the reverse of this order.
- **Computing dish status**: after changing `stock`, the transaction locks the `dish_status` rows of the dishes that use the changed ingredients with `SELECT ... FOR UPDATE`, and only then reads the stock of every ingredient in the recipes and recomputes according to section 3.4 of the specification. Reading stock before locking is wrong: two transactions that change two different ingredients of the same dish would not see each other's change, and the dish could sit at Available when it should be Sold out.
- **Dish version**: each time a dish changes status, or an ingredient's stock-check flag changes, the transaction runs `UPDATE menu_version SET seq = seq + 1 RETURNING epoch, seq`. Locking this row makes the `seq` order match the commit order; a PostgreSQL `SEQUENCE` does not guarantee that.
- **Bumping `epoch`** (after restoring Inventory from a backup): one transaction locks every `dish_status` row, runs `UPDATE menu_version SET epoch = epoch + 1, seq = seq + 1`, and only then reads stock, recomputes and rewrites every `dish_status` row with the new `epoch` and `seq`, including dishes whose status did not change. The transaction emits `IngredientCheckChanged` for every ingredient so that the Kitchen has flags for the new generation, and does not emit `DishStatusChanged`: branches see the new `epoch` in the next `Heartbeat` and then fetch the snapshot themselves.
- **Invariants** (run after every test): an ingredient's `stock.reserved` equals the sum of `quantity` over the `inventory_reservations` rows with `outcome IS NULL`; and every row with `outcome IS NULL` belongs to an order currently at `DANG_GIU`.
- **Outbox relay with 2 instances**: read in ascending `id` with `FOR UPDATE SKIP LOCKED`. The two instances may relay out of order relative to each other, and so may one instance, since a row Kafka did not acknowledge stays unsent while later rows of the same batch are marked sent; this is acceptable because every receiver processes by the state table, not by message order. The row locks are held while the relay waits for Kafka (up to `message.timeout.ms`), which blocks no business transaction because those only insert outbox rows. `payload` holds the whole envelope, which is the Kafka message value; `msg_key` is the order ID, or the dish or ingredient ID on `menu-events`. At the branch, the condition of operation (4) in section 5 is what guarantees this.

## 4. Kitchen DB schema

The Kitchen keeps everything about an order in exactly one row of `kitchen_orders` (BR8); a ticket, a Cancel-pending record and a Failed result differ only in the `status` column.

```sql
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

-- alerts, processed_events and outbox_events: same as the Inventory DB
```

Rules that go with the schema:

- **One entry point for every change**: messages from `kitchen-orders`, messages from `cancel-events` and the three staff buttons all run the same sequence (the buttons skip the first step: they act only on a row that exists, and answer 404 otherwise): insert a `CHUA_CO` row if none exists, `SELECT ... FOR UPDATE`, apply table 3.2, write the outbox, commit (section 13.4 of the specification).
- **The branch that sent a cancel request** is taken from the topic name, not from `branch_id` in the message, and is then added to `cancel_branches` if it is not already there, unless the request is ignored as coming from the wrong branch (below). That branch's reason is written to `cancel_reasons`; a repeated request from the same branch does not overwrite the existing reason.
- **When `OrderReserved` reaches a `HUY_CHO_DON` row**: if `origin_branch = ANY(cancel_branches)`, the row moves to `DA_HUY`, `close_reason` takes the origin branch's reason from `cancel_reasons`, and `ReleaseRequested` is emitted together with `OrderCancelled`. Otherwise `cancel_branches` and `cancel_reasons` are cleared, the row moves to `CHO_NAU`, and an `alerts` row of kind `HUY_SAI_CHI_NHANH` is written with the list of dismissed branches.
- **A wrong-branch cancel request** that arrives when the row already has `origin_branch`: keep the status, send no reply, and write an `alerts` row of kind `HUY_SAI_CHI_NHANH`.
- **The `alerts` table**: the Kitchen uses two kinds, `CAN_KIEM_TRA` and `HUY_SAI_CHI_NHANH`, inserted the same way as at Inventory.
- **The red warning on the ticket** is a display-time join between the `reserved` of `CHO_NAU` tickets and the `flagged_ingredients` rows with `needs_check = TRUE`. A `flagged_ingredients` row is overwritten only when the message's `(epoch, seq)` is greater.
- **The release command is stored durably before it is sent**: `ReleaseRequested` sits in `outbox_events` in the same transaction as the `status` change, so if Inventory is down the command is still there (scenario 4).
- **Cancel requests in practice** (built in step 5):
  - A request is decided even without a reason from the customer-cancel group of section 1 (the branch validates reasons, BR9); it is logged, never sent to the dlq. A Queued ticket cancelled that way gets `close_reason = CHANGED_MIND`, as a Cancel-pending record does on the order's arrival (rule "Tickets in practice").
  - A Cancel-pending record keeps every asking branch and its first reason. A repeat from a listed branch changes nothing except filling in a reason that was missing, and gets `CancelPending` again. Cancelling a Queued ticket writes the origin branch and its reason to `cancel_branches` and `cancel_reasons`; at Cooking, Completed, Cancelled or Failed they are not written.
  - `CancelPending` carries the asking branch as `branch_id` (the one exception to "Tickets in practice"), an empty payload, and the request as `causation_id`. A branch whose request is later dismissed hears nothing more.
  - A request reaching a Failed record with no origin (left by a malformed `OrderFailed`) gets the stored `OrderFailed` at the asking branch.
  - The `alerts` row of kind `HUY_SAI_CHI_NHANH` has `detail = {origin_branch, dismissed}`: the order's origin and the branches whose requests were ignored or dismissed. Each new message raises its own row.
  - **Message types and topics:** Inventory's `OrderReserved` and `OrderFailed` are accepted only from `kitchen-orders`, `CancelRequested` only from `cancel-events.<branch>`; at Inventory, `ReleaseRequested` and `StockConsumed` only from `stock-commands`. A message of those types on another topic counts as unreadable (5 attempts, the dlq, a `CAN_KIEM_TRA` alert).
- **Tickets in practice** (built in step 4):
  - `OrderFailed` reaching a Queued or Cooking ticket changes nothing and is logged: table 3.2 has no such row, and Inventory keeps one result per order (BR12). Reaching a Cancel-pending record it gives Failed and nothing more, as table 3.2 says, without comparing the recorded cancel branches with the origin branch.
  - An `OrderReserved` without `origin_branch` cannot be recorded and counts as unreadable (5 attempts, then the dlq). An `OrderFailed` with a missing field is still recorded as `THAT_BAI`, with NULL in that column, because recording the result matters more (prohibition 11). A `created_at` that cannot be read is kept as NULL `order_created_at`.
  - When a Cancel-pending record becomes Cancelled but holds no reason for the origin branch, `close_reason` is `CHANGED_MIND`.
  - Reject takes a reason from the Kitchen-rejection group of section 1, otherwise 400. Spoiled ingredients go only with `SPOILED_INGREDIENT` (400 otherwise), at least one is needed, each must be on the ticket's `reserved[]`; the list is stored and sent without repeats, sorted. The reason is checked before the ticket's status.
  - The buttons answer 404 when there is no ticket (no row, or `CHUA_CO`), 409 with `{message, status}` when the record is in any other status than the one required (Cancel-pending and Failed records included), and 200 with the updated ticket. Emitted messages carry the origin branch as `branch_id`; those from a button have no `causation_id`.
  - `GET /tickets` lists Queued and Cooking tickets by `order_created_at` (unknown last), then by order ID. `warnings` holds the flagged ingredient IDs of a Queued ticket, sorted; a Cooking ticket has none.
  - `IngredientCheckChanged` with a malformed payload counts as unreadable. The first message about an ingredient creates its row even when `needs_check` is false.

## 5. Branch DB schema (POS and Online)

The Local Order DB and the Online Order DB share one schema; what is new compared with the base flow is the rank column, the cancel flag and the "send attempted" flag on the send queue.

```sql
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

-- processed_events: same as the Inventory DB
```

Added in revision 8, as migration `002`:

```sql
-- The dish catalogue of this branch, loaded from backend/seed/menu.json on every start.
-- It serves the order form, also while the branch is offline (scenario 10).
CREATE TABLE dishes (
  dish_id TEXT PRIMARY KEY,
  name    TEXT NOT NULL
);
```

`POST /orders` rejects an order whose `dish_id` is not in `dishes` (HTTP 400, section 4 of the specification, step 1). This checks only that the dish exists; whether it is Sold out is a matter for the screen (point 5 in section 8), and whether it can be made is decided by Inventory.

Five conditional writes decide the correctness of the branch side:

```sql
-- (1) The sender sets the flag BEFORE calling Kafka, commits, and only then sends.
--     For an entry without the flag, run this only when a connectivity probe to Kafka has just succeeded.
--     No row changed: the entry was cancelled locally, skip it.
UPDATE outbox_events SET attempted = TRUE
 WHERE id = :id AND sent_at IS NULL RETURNING id;

-- (2) Cancel: one transaction, lock the order row first and only then decide.
SELECT status_rank, cancel_flag FROM orders WHERE order_id = :o FOR UPDATE;
--   No row:                  return 404, stop.
--   status_rank = 2:         return 409, stop.
--   cancel_flag <> 'KHONG':  return 202, stop. Do not insert a second HUY entry.
DELETE FROM outbox_events
 WHERE order_id = :o AND kind = 'TAO_DON' AND attempted = FALSE RETURNING id;
--   1 row: local cancel.
--     UPDATE orders SET status = 'DA_HUY', status_rank = 2, close_reason = :r
--      WHERE order_id = :o;
--   0 rows: go through the Kitchen.
--     INSERT INTO outbox_events (event_id, order_id, kind, topic, payload)
--     VALUES (:event_id, :o, 'HUY', :topic, :payload);
--     UPDATE orders SET cancel_flag = 'DANG_YEU_CAU', cancel_requested_at = now(),
--            cancel_message = NULL
--      WHERE order_id = :o;

-- (3) Apply a status message: forward only, never backward (BR3).
UPDATE orders SET status = :s, status_rank = :rank,
       close_reason = COALESCE(:reason, close_reason),
       cancel_flag = CASE WHEN :rank = 2 THEN 'KHONG' ELSE cancel_flag END
 WHERE order_id = :o AND status_rank < :rank;

-- (4) CancelPending: only when the order is not in a terminal status and is waiting for a reply from the Kitchen.
UPDATE orders SET cancel_flag = 'BEP_KHONG_NAU'
 WHERE order_id = :o AND status_rank < 2 AND cancel_flag = 'DANG_YEU_CAU';

-- (5) CancelRejected: turn the flag off and record the message, at any rank.
UPDATE orders SET cancel_flag = 'KHONG', cancel_message = :msg
 WHERE order_id = :o;
```

- (1) and (2) lock the same `outbox_events` row, so exactly one side wins (scenario 37). If the process dies between setting the flag and sending, the entry still carries the flag and is resent; that order can no longer be cancelled locally, as BR9 requires.
- **Starting a send attempt**: before running (1) for an entry without the flag, the sender probes the connection to Kafka, for example by fetching the cluster metadata with a short timeout. If the probe fails, the sender neither sets the flag nor sends, so an order created while offline can still be cancelled locally (scenario 10). A wrong probe result is safe in either direction. A false "disconnected" only makes the entry leave later. A false "connected" means the entry carries the flag, the send fails and is retried as in scenario 12. An entry that already has the flag is resent without probing first. The result of the most recent probe is the "connection status" returned by the branch's `GET /monitor`.
- (2) locks the `orders` row before deleting the entry, so two cancel presses in quick succession run one after the other: the second one sees that the order is already in a terminal status or already has the flag, and stops. Operation (3) also writes to that `orders` row, so a terminal status message arriving in between does not leave a dangling cancel flag on a closed order.
- The lock order at the branch is the `orders` row first, the `outbox_events` row second. Operation (1) locks only `outbox_events`, and operations (3), (4), (5) lock only `orders`, so there is no cross-locking.
- The sender takes only the unsent row with the smallest `id` for each `order_id`. A cancel entry therefore never goes before the create-order entry of the same order, while other orders are not blocked (BR9).
- `CancelPending` and `CancelRejected` do not touch `status`.
- `menu_cache` is overwritten only when the message's `(epoch, seq)` is greater than that of the existing row; the snapshot is merged by the same rule, not deleted and reloaded (BR10).
- The rank condition of write (4) never decides on its own: write (3) turns the flag off whenever an order becomes terminal, a local cancel closes an order whose flag is off, and write (2) refuses a terminal order, so no terminal order has the flag `DANG_YEU_CAU`. It stays as written, as a guard.

Added in revision 14, as migration `003`:

```sql
-- Flow D: status messages this branch could not read (moved to the dlq) or did not recognise
-- (ignored), section 9 of the specification. Same shape as the alerts table of section 3.
CREATE TABLE alerts (
  id               BIGSERIAL PRIMARY KEY,
  kind             TEXT NOT NULL CHECK (kind IN ('CAN_KIEM_TRA')),
  order_id         UUID,
  event_id         UUID,
  source_topic     TEXT NOT NULL,
  source_partition INT NOT NULL,
  source_offset    BIGINT NOT NULL,
  detail           JSONB NOT NULL DEFAULT '{}',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (kind, source_topic, source_partition, source_offset)
);
```

The `alerts` table stays at the branch: it is not in the publication to the Central Order Replica.

**The branch in practice** (built in step 6):

- **Send states.** `GET /orders` gives each order the state of its create-order entry (`send_state`) and of its latest cancel entry (`cancel_send_state`): `CHUA_GUI` (no flag: "Not sent, kitchen has not received it"), `DANG_GUI` (flag, no acknowledgement: "Sending, unknown whether the kitchen has received it"), `DA_GUI` (acknowledged by Kafka, which says nothing about Inventory or the Kitchen). `send_state` is null once a local cancel discarded the entry; `cancel_send_state` is null if no cancel was queued. These carry the texts of BR5.
- **The probe** is a cluster metadata request through the sender's own Kafka client, with a 2-second timeout; it succeeds if any broker answers. The sender probes before every round that has an entry without the flag, and at least every 5 seconds otherwise, so the connection status of `GET /monitor` stays current. While entries with the flag are failing, one round can take up to `message.timeout.ms` (30 s) plus 10 s, so the status can be that old; `checked_at` shows its age.
- **Retries.** A round with a failed send, an entry held back by a failed probe, or any error waits 0.5 s, doubling up to 5 s, then goes again. A message the producer refuses outright (for example over the 1 MB limit) fails like any other send and stays queued with its flag: the quarantine queue is out of scope (section 15 of the specification); the other orders' entries are still sent.
- **One sender per branch.** Only the sender sets `sent_at`, which is what keeps a cancel entry behind its create-order entry; a branch runs one instance (section 13.6 of the specification).
- **A leftover cancel entry.** A cancel entry queued while the order was open is still sent if the order reaches a terminal status first. The Kitchen returns its stored result and the rank rule ignores it, so this is harmless.
- **Messages the branch cannot apply.** A status message for an order the branch does not have is logged as a warning and recorded in `processed_events`; it raises no alert. A message whose topic names another branch counts as unreadable (5 attempts, the dlq, an alert). A `reason_code` that is not text is dropped; any other value is stored as received.
- **`OrderCreated`** carries `created_at` (the branch's clock, UTC), `channel` (`ONLINE` for the Online branch, `POS` for the others) and `items[{dish_id, name, quantity}]` with the names from `dishes`.
- **`cancel_message`** holds the fixed English text "Cannot cancel: the kitchen has started cooking"; the screens show it in Vietnamese.
- **`GET /monitor`** lists, besides the connection status: `waiting_to_send`, the number of entries Kafka has not acknowledged (attempted ones included: without the acknowledgement the branch does not know whether Kafka has them); `awaiting_inventory`, orders in `CHO_KHO` created more than N = 10 minutes ago, with the time waited and the cancel flag; `about_to_expire`, orders still in `CHO_KHO` whose create-order entry is unacknowledged and was created more than X − 1 hour ago, with `expires_at` (an order already past X stays listed: Inventory will fail it when it arrives, and the branch may not decide Failed itself); `cancel_requested`, orders with the flag on and the time waited; `message_alerts`, the number of `alerts` rows and the 20 latest. The two choices on orders past X and on attempted entries were confirmed by @Naul on 22 Nov 2026.

### Replication to the Central Order Replica

The specification requires the branch order DBs to replicate asynchronously to the Central Order Replica (section 13.5) and the Management report to show a "data as of" time for each branch (section 8). There is no existing reporting service to reuse, so both are built in this project. This part is the choice of point 12 in section 8, agreed on 21 Nov 2026. The publication and subscription below were trial-run on 21 Nov 2026 (section 9); the Order Query Service was not.

- **What replicates:** only `orders` and `replication_heartbeat`. The send queue, the dish cache and `processed_events` stay local.
- **Mechanism:** PostgreSQL logical replication. Each branch DB runs with `wal_level=logical` and publishes the two tables. The central DB has the same two tables and one subscription per branch.
- **`branch_id`:** every `orders` row carries the branch's own id, taken from the service configuration, so that rows from different branches can be told apart in the central DB. `order_id` is a UUID, so rows from different branches never collide.
- **"Data as of":** each branch service updates its single `replication_heartbeat` row every 5 seconds (proposed). The value that has reached the central DB is that branch's "data as of" time. When replication from a branch is cut, its value stops moving while the other branches' values keep moving (scenario 55).
- **Reading:** the Order Query Service reads the central DB only, never a branch DB.

```sql
-- On each branch DB
CREATE PUBLICATION central_pub FOR TABLE orders, replication_heartbeat;

-- On each branch DB, every 5 seconds
INSERT INTO replication_heartbeat (branch_id, beat_at) VALUES (:branch, now())
ON CONFLICT (branch_id) DO UPDATE SET beat_at = EXCLUDED.beat_at;

-- On the central DB, once per branch
CREATE SUBSCRIPTION sub_pos01
  CONNECTION 'host=<branch-db-host> dbname=<branch-db> user=<replication-user>'
  PUBLICATION central_pub;
```

## 6. API

Each service exposes only the APIs that a person or a screen needs; services do not call each other's APIs, except for the dish snapshot. Request and response bodies are JSON.

| Service | API | What it does | Returns |
|---|---|---|---|
| Branch | `POST /orders` | Validates the data, generates `order_id`, stores the Awaiting Inventory order and the create-order entry in one transaction | 201 with the order as `GET /orders/{id}` shows it; 400 if the data is invalid: no items, a missing field, a quantity that is not a positive whole number, or a dish not in `dishes` (BR9). Every invalid input at the branch is 400, not FastAPI's 422 |
| Branch | `GET /dishes` | The dish catalogue from the branch's own `dishes` table; answers while the branch is offline | 200 |
| Branch | `POST /orders/{id}/cancel` | Runs operation (2) in section 5 with `reason_code` | 200 `DA_HUY` for a local cancel; 202 `DANG_YEU_CAU` if it goes through the Kitchen or a cancel request is already pending; 409 if the order is already in a terminal status; 404 if the order does not exist; 400 if `reason_code` is not a customer cancel reason (checked first). The body is the order |
| Branch | `GET /orders`, `GET /orders/{id}` | Reads orders with the cancel flag and message and the send states ("The branch in practice", section 5); the list holds the 200 most recent | 200; 404 for an unknown order |
| Branch | `GET /menu` (phase 2) | Reads `menu_cache`, with a `stale` flag when nothing has been heard from Inventory for more than N minutes | 200 |
| Branch | `GET /monitor` | Flow D: connection status, number of entries waiting to be sent, orders in Awaiting Inventory longer than N minutes, orders about to pass X, orders with the cancel flag, message alerts ("The branch in practice", section 5) | 200 |
| Kitchen | `GET /tickets` | Queued and Cooking tickets, with warnings for flagged ingredients | 200 |
| Kitchen | `POST /tickets/{order_id}/start` | Queued → Cooking, emits `StockConsumed` | 200; 409 with the current status if the ticket is no longer Queued |
| Kitchen | `POST /tickets/{order_id}/reject` | Queued → Cancelled with `reason_code`, `spoiled_ingredients[]`; emits `OrderCancelled` and `ReleaseRequested` | 200; 409 as above; 400 if the reason is Spoiled ingredient but no ingredient is given, or an ingredient does not belong to the ticket |
| Kitchen | `POST /tickets/{order_id}/complete` | Cooking → Completed, emits `OrderCompleted` | 200; 409 if the ticket is not Cooking |
| Kitchen | `GET /alerts` | Flow D: orders that need review and wrong-branch cancel requests; filterable by `kind` | 200 |
| Inventory | `GET /menu/snapshot` (phase 2) | Status and version of every dish, including Hidden dishes, with the current `epoch` | 200 |
| Inventory | `POST /ingredients/{id}/clear-check` | Clears the stock-check flag after the check is done; optionally takes `counted_on_hand`, the counted on-hand stock | 200; 409 if `counted_on_hand` is less than the reserved quantity |
| Inventory | `POST /stock/receipts` | Stock receipt: adds to `available` for one ingredient | 200 |
| Inventory | `GET /stock` | The four stock quantities and the stock-check flag; used for testing, the demo and Flow D's list of ingredients awaiting a stock check | 200 |
| Inventory | `GET /alerts` | Flow D: orders that need review and unmatched commands; filterable by `kind` | 200 |
| Inventory, Kitchen | `GET /monitor` | Flow D: age of the oldest unread message on each topic, with a warning when it exceeds the slow-consumer threshold | 200 |
| Inventory | `POST /admin/epoch/bump` (phase 2) | Runs the `epoch` bump procedure in section 3; used after restoring Inventory and for scenario 20 | 200 with the new `epoch` |
| Reporting | `GET /reports/summary` | For each branch: the "data as of" time, the number of orders by status, and the number by reason for Cancelled and Failed orders; reads the Central Order Replica only | 200 |

- **The screens** (the `frontend` module in section 2 of document 03) are a client of the APIs in this table and use nothing else: no direct DB access, no Kafka. They show the statuses the services return and decide none of their own; the only rule enforced on screen alone is point 5 in section 8. Each service publishes the OpenAPI document that FastAPI generates, and the screens' TypeScript types are generated from it.
- **The three Kitchen buttons** run the same row-locking sequence as the consumer, without inserting a `CHUA_CO` row (section 4). A 409 here is the normal outcome of the race between Cancel and Start cooking (BR7); the UI only needs to reload the ticket.
- **`POST /orders` does not wait for Inventory**: the Reserved or Failed result comes later through `status-events`. The UI re-reads the order with `GET /orders/{id}`.
- **`counted_on_hand` of `clear-check`** is the on-hand stock, that is, available stock plus reserved (section 3.3 of the specification). Inventory sets `available = counted_on_hand − reserved`. If the result is negative it returns 409: the tickets still holding that ingredient must first be rejected through Flow A. If `counted_on_hand` is not sent, `available` stays unchanged.
- **`clear-check` and `receipts`** can both make a dish change status, so they rerun Flow C's dish-status computation in the same transaction. `clear-check` also emits `IngredientCheckChanged`.
- **The Inventory stock APIs as built in step 3**: an unknown ingredient gives 404 on `clear-check` and `receipts`; invalid input gives 422 (a receipt quantity of 0 or less, a negative `counted_on_hand`, more than 12 digits or 3 decimals). The 409 of `clear-check` carries `{message, reserved}`. `receipts` and `clear-check` return the ingredient's row as `GET /stock` shows it (the four quantities, `needs_check`, `name`, `unit`). `clear-check` on an ingredient that is not flagged returns 200 and sends nothing; with `counted_on_hand` it still sets `available`, so it doubles as a stock adjustment. A receipt never clears the flag. Each request commits before it answers. The dish-status computation of these two APIs comes with phase 2.
- **Management's report** is served by the Order Query Service through `GET /reports/summary`, from the Central Order Replica (section 5). It counts order statuses at the branches only; a Cancel-pending record at the Kitchen is not a terminal status and is not counted (section 8 of the specification).

## 7. Implementation order

Phase 1 has seven steps covering Flows A, B, D and reporting, with 40 scenarios; phase 2 is Flow C with 4 scenarios. Each step builds on the previous one; steps 2–3 (Inventory) and step 6 (branch) can be done in parallel once step 1 is finished.

| Step | Service | What to build | Scenarios that must pass |
|---|---|---|---|
| 1 | Shared | Message envelope, `processed_events`, outbox relay, the consumer following the 5 steps of section 13.3, sending broken messages to the dlq and writing `alerts` | 26, 29, 31 |
| 2 | Inventory | Receive `OrderCreated`: the BR12 record, the X-hour limit, data validation, the conditional reserve with `NOT needs_check`, emit `OrderReserved` or `OrderFailed` | 9, 15, 16, 24, 30, 39, 42, 44 |
| 3 | Inventory | Receive `ReleaseRequested` and `StockConsumed`: release, waste, flagging for stock check, consumed; `menu_version` and emitting `IngredientCheckChanged`; the clear-flag and stock-receipt APIs | 5, 6 (waste and release part), 22, 43, 48 (flag cleared and reservable again part), 49 |
| 4 | Kitchen | The main path of table 3.2: create the ticket, Start cooking, Reject, Complete, record the Failed result; receive `IngredientCheckChanged` into `flagged_ingredients` and show the red warning on the ticket | 4, 6 (ticket warning part), 48 (warning disappears part), 50, 52 |
| 5 | Kitchen | Receive `CancelRequested`: Cancel-pending, the race with Start cooking, the origin-branch check | 1, 2, 3, 8, 23, 25, 27, 28, 33, 34, 35, 51 |
| 6 | Branch | Apply status messages by rank, the connectivity probe and the "send attempted" flag, local cancel, sending cancel requests, the "Cancel requested" flag, `GET /monitor` | 7, 10, 12, 36, 37, 53, 54 |
| 7 | Reporting | The Order Query Service, replication to the Central Order Replica and the "data as of" time (section 5) | 55 |
| Phase 2 | Inventory, branch | Flow C: computing dish status, `DishStatusChanged`, heartbeat, snapshot, `menu_cache`, the `epoch` bump procedure | 18, 19, 20, 21, the "dish becomes Sold out" part of 6 and the "dish returns to Available" part of 48 |

Each scenario has two test levels. At its own step, a scenario is tested at handler level: the test feeds messages straight into one service's handler and checks the DB and the outbox rows, with no other service needed. Some scenarios only run in full when all the services are present, for example 24 needs the branch and the Kitchen, and 3 needs all three sides; their end-to-end versions run after step 6. Scenario 42 takes as its main test one that calls Inventory's handler from two threads on the same DB; having each of two instances receive one order is only a supplementary check.

Once step 6 is done, run the demo set 1, 3, 4, 10, 36 on all the services. Scenarios 28 and 42 need two instances of Kitchen and Inventory; scenario 31 needs all 3 brokers.

## 8. Design choices to confirm before coding

The twelve points below are design choices made by this document and not present in the specification; each comes with a proposal, and a point is ticked once it is agreed. Points 1–6 date from the first version, points 7–10 were added in revision 2, point 11 in revision 3 and point 12 in revision 4.

**Status:** all twelve points were agreed by @Naul exactly as proposed on 21 Nov 2026. Point 1 no longer applies: on 21 Nov 2026 it was decided to build the project from scratch, with no B5 codebase, so the names in this document are the ones to use. One accompanying task remains: trial-running how Kafka assigns partitions (point 6). Of the five points in section 11 of the specification, the three that change behaviour were confirmed on 21 Nov 2026; the two still open are configuration values.

- [x] **1. Naming versus the B5 baseline.** Proposal: B5's names win wherever B5 already has one (the order table, the outbox, `OrderCreated`); this document names only the new parts. Someone who knows the B5 code reviews the tables in sections 2 to 6 once before the work is split up. *No longer applies since 21 Nov 2026: there is no B5 codebase.*
- [x] **2. Where the Kitchen replies to a cancel request.** Proposal: keep it as in section 2. `CancelPending` goes to the topic of the requesting branch because only that branch has a flag to update; the final result always goes to the origin branch. For an honest branch, the two are the same branch.
- [x] **3. "Return the stored result".** Proposal: emit a new message with a new `event_id`. If the old outbox row were resent, the receiver would already have that `event_id` in `processed_events` and would ignore it, which means no reply at all; a new message is safely re-applied by the receiver thanks to the rank rule and BR12.
- [x] **4. The `seq` counter.** Proposal: one row in `menu_version`. The cost is that transactions which change a dish's status have to queue on this row; that is rare, because most reservations change no dish's status.
- [x] **5. A Sold out dish while the data is fresh.** Proposal: block only in the UI; `POST /orders` does not check `menu_cache`. Inventory is the only place that rejects an order because of ingredients; adding a 409 at the branch would add a second rejection path based on data that is only a hint.
- [x] **6. Partition counts.** Proposal: 2 for `order-events.*`, `cancel-events.*`, `kitchen-orders` and `stock-commands`; 1 for `status-events.*`, `menu-events` and `dlq`. The partition key is the order ID, so an order still stays within one partition. In scenario 42, pick two order IDs that fall into two different partitions and check in the logs that the two Inventory instances each process one order; how Kafka assigns partitions to instances needs a trial run to confirm.
- [x] **7. The `alerts` table.** Proposal: one table at Inventory and one at the Kitchen for the three kinds of Flow D alerts, read through `GET /alerts`. The alternative is to log only, but then scenario 29's "needs review" mark has nowhere to be stored, and scenarios 22, 27 and 34 would have to be checked by scanning logs.
- [x] **8. The `clear-check` parameter.** Proposal: `counted_on_hand` is the on-hand stock, and Inventory subtracts the reserved quantity itself. If the team wants the person doing the stock check to enter the available stock directly, rename the parameter and drop the subtraction.
- [x] **9. The `epoch` bump procedure.** Proposal: as in section 3, invoked through `POST /admin/epoch/bump`. Restoring Inventory from a backup remains a manual task outside the scope; this procedure only covers the "bump the epoch" part that the specification requires the system to guarantee.
- [x] **10. Where Inventory returns the stored result.** Proposal: only to the origin branch, not re-emitted to the Kitchen. The Kitchen already received the original message through the outbox, and re-emitting to the Kitchen would only make it reply to the branch one more time.
- [x] **11. How to probe connectivity before a send attempt.** Specification v1.5 states that the sender starts a send attempt only when the connectivity probe succeeds (BR9); the choice made in this document is how to probe. Proposal: fetch the Kafka cluster metadata with a short timeout, and use that same result as the connection status in `GET /monitor`. The alternative is to let the cashier switch on an offline mode manually, but then the correctness of scenario 10 depends on a human action.
- [x] **12. Replication and reporting.** The specification asks for asynchronous replication of the branch order DBs to the Central Order Replica and a "data as of" time per branch, but does not say how. Proposal: PostgreSQL logical replication of `orders` and of a `replication_heartbeat` table, a `branch_id` column on `orders`, and one read API on the Order Query Service, as in sections 5 and 6. The alternative is to publish order changes to Kafka and build the replica from a consumer, which adds a topic and a service for something the database already does.

## 9. Trial-run results

This section records what has actually been run, to distinguish it from what has only been checked by reading.

The run on 21 Nov 2026 used PostgreSQL 16.2 and a temporary script that is not part of the project source. The DDL in sections 3, 4 and 5 and the five operations in section 5 were extracted verbatim from this document; the rules written in prose in sections 3 and 4 were implemented minimally, just enough to run. The run had no Kafka: message order was simulated by calling the operations in the desired order, and races were produced with two connections running at the same time. The most recent run was on revision 4; all 45 checks passed.

| Area | Checked | Scenarios partly covered |
|---|---|---|
| Schema | The DDL of all three DBs can be created | |
| Inventory | Reserve, consumed, release and waste match the accounting table; the two deduplication layers; an unmatched command and a command reaching a Failed record each write exactly one `alerts` row; the two invariants return 0 rows; `clear-check` with `counted_on_hand` | 5, 6, 22, 30, 43, 44 |
| Inventory, races | 200 runs of two orders competing for one ingredient: exactly one order is reserved every time | 42 |
| Dish status | Without locking `dish_status` the wrong status is reproduced; locking before reading stock gives the right result in both lock-acquisition orders; bumping `epoch` rewrites every row | |
| Branch | Local cancel; applying messages by rank; `CancelPending` arriving after `OrderFailed` is ignored; `CancelRejected` arriving before and after Completed; merging `menu_cache` by version; the `replication_heartbeat` upsert keeps one row per branch | 7, 8, 10, 19, 20, 36 |
| Branch, races | 200 runs of the sender and the cancel button at the same time (83 local cancels, 117 through the Kitchen); 200 runs of two cancel commands at the same time; 200 runs of a cancel and a Completed message at the same time. The first version's approach reproduces both defects described above | 37 |
| Kitchen | Cancel arriving before the order; duplicate order arrival; wrong-branch cancel before and after the order arrives; reason per branch; cancel while Cooking; the ticket warning; the "needs review" mark is not duplicated | 1, 2, 6, 23, 27, 29, 34, 35 |
| Kitchen, races | 200 runs of Cancel and Start cooking at the same time (cooking won 98 times, cancel won 102 times); 200 runs of an order and a cancel request for the same order ID arriving at the same time | 3, 28 |
| Replication (separate run, step 0) | On PostgreSQL 16.14, the publication and subscription at the end of section 5 between a branch DB and the central DB: an order and a heartbeat arrive in about 0.2 s; with the subscription disabled for 5 s the central `beat_at` stays still while the branch keeps beating, then catches up in about 0.2 s; with the central DB paused for 5 s, three orders written meanwhile arrive once it is back. The one-off script was removed when the environment moved to Docker Compose; the `replication-init` container now sets replication up and `bin/chaos cut-replication` cuts it (section 2 of document 03) | 55 (the "data as of" part) |

The two statements added in revision 8 (`stock.name`, the `dishes` table) run in the schema tests of each service, not in the trial runs above.

Not yet checked:

- Everything that needs a real Kafka: scenarios 4, 12, 24, 25, 31 and the consumer part of scenarios 26 and 29.
- The X-hour limit check and creation times in the future (scenarios 15, 16).
- The connectivity probe before a send attempt (section 5), because it needs a real Kafka.
- Scenarios 9, 18, 21, 33, 39 and the new scenarios 48–55.
- The APIs in section 6.
- The `IngredientCheckChanged` emission part of the `epoch` bump procedure.
- `GET /reports/summary`. Logical replication itself was trial-run separately; see the last row of the table above.

These trial runs only confirm the design; they do not replace the automated tests that section 12 of the specification requires.
