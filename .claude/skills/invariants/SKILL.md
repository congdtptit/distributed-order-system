---
name: invariants
description: Check the two stock-accounting invariants of the Inventory DB (reserved stock equals the sum of held lines; every held line belongs to a Held order), plus negative stock. Use after a demo run, an end-to-end test or any manual change to Inventory data, or when the user asks whether the stock figures are consistent.
argument-hint: "[postgres DSN, default: the inventory-db container]"
allowed-tools: Bash(docker compose exec tools python scripts/check_invariants.py*)
---

# Check the Inventory invariants

Run the script; do not write the queries by hand:

```
docker compose exec tools python scripts/check_invariants.py $ARGUMENTS
```

With no argument it connects to the `inventory-db` container of `compose.yaml`. To check another database, pass its DSN.

The script exits 0 and prints one summary line when every check returns no rows. Otherwise it exits 1 and prints the offending rows of each failed check.

## The checks

From section 3 of `docs/02-detailed-design.md` ("Invariants"):

1. For each ingredient, `stock.reserved` equals the sum of `quantity` over the `inventory_reservations` rows with `outcome IS NULL`.
2. Every row with `outcome IS NULL` belongs to an order whose `inventory_orders.status` is `DANG_GIU`.

The script also reports rows that the table constraints should already make impossible: negative `available`, `reserved`, `consumed` or `wasted`.

## Handling the result

A failed invariant is a bug in Inventory, not in the data. Report the rows to the user in Vietnamese, with the order and ingredient ids, and do not repair the data. Section 15 of document 01 says what the invariants cannot catch: a reservation stuck in Held because a release command was lost still passes both checks.
