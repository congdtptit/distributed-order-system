---
paths:
  - "backend/order-service/**"
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

## Code map

| File | Content |
|---|---|
| `src/order_service/orders.py` | Statuses, ranks, flags, send states; `load_dishes`; `create_order` (validation, order and create-order entry); `cancel_order` (write (2)); `get_order`, `list_orders` with the send states |
| `src/order_service/statuses.py` | `branch_handlers(branch)`: writes (3), (4), (5) for the messages of `status-events.<branch>`; a message from another topic is refused |
| `src/order_service/sender.py` | `SendQueue`: heads per order, the probe, write (1) (`start_attempts`), sending, `ConnectionStatus` for `/monitor`; `run` never stops on an error |
| `src/order_service/monitor.py` | `monitor_view` and `MonitorLimits` (N, X, X − 1 h) |
| `src/order_service/app.py` | Dishes loaded on start; consumer and sender threads; the APIs; invalid input is 400 |
| `tests/branch_support.py` | `place`, `cancel`, `mark_attempted`, `deliver` (through `handle_once`), `queued_envelope` to hand the branch's real messages to Inventory and the Kitchen |

## Scenarios of this module

Step 6 in section 7 of document 02: 7, 10, 12, 36, 37, 53, 54, all passing since 22 Nov 2026 (10 and 36 also end to end with a real network cut of the `pos01` container). The branch side of 1, 3, 4, 8, 23, 24, 31 and 33 passes too. Phase 2: 19, 21 and the branch part of 20.
