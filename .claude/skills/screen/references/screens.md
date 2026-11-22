# The screens

One entry per screen: who uses it, where it is specified, which APIs it calls (section 6 of `docs/02-detailed-design.md`), the states it must handle, when it is built, and the sizes to screenshot. "01" is `docs/01-business-spec.md`, "02" is `docs/02-detailed-design.md`.

This file names what to show and points to the section that says how. It does not restate the rules; read the sections.

## branch

- **Route:** `/branch/:branchId` (`POS01`, `POS02`, `ONLINE`). Users: cashier (POS), customer (Online).
- **Specified in:** 01 section 4 (placing an order), section 6 "Branch side" and the decision table, table 3.1 with the ranks and the cancel flag, section 8 (the four Branch rows), section 10 (reasons); 02 section 2, the table on applying status messages.
- **APIs:** `GET /dishes`, `POST /orders`, `POST /orders/{id}/cancel`, `GET /orders`, `GET /orders/{id}`, `GET /monitor` of that branch.
- **Must handle:**
  - each of the five order statuses, with its rank;
  - the cancel flag in its three values, and `cancel_message` ("Cannot cancel: the kitchen has started cooking");
  - the Cancel button hidden at rank 2; a pending request (`DANG_YEU_CAU`) offers no second cancel;
  - the four results of cancel: 200 `DA_HUY` (local cancel), 202 `DANG_YEU_CAU`, 409, 404;
  - the cancel dialog: a reason is mandatory, from the customer-cancel group of 01 section 10;
  - the offline case: an attempted order's cancel request is not a commitment, and the screen must say so (01 section 6, "Branch offline");
  - the Flow D alerts of 01 section 8: an order in Awaiting Inventory for more than N minutes, with a Request cancellation button; an entry close to the X-hour limit; flagged orders with the time waited;
  - connection status and the number of entries waiting to be sent, from `GET /monitor`.
- **Dishes for the order form:** `GET /dishes` (02 section 5, revision 8), which answers offline too. The old open question on this is closed.
- **Send states:** `send_state` and `cancel_send_state` (`CHUA_GUI`, `DANG_GUI`, `DA_GUI`) carry the texts of BR5 ("The branch in practice", 02 section 5).
- **Phase 2 (Flow C):** blocking a Sold-out dish while the data is fresh, and "Dish availability may have changed" / "May be sold out" when it is stale (01 section 7, the table; 02 section 8, point 5). Uses `GET /menu`.
- **Built in:** step 6b; the Flow C part in phase 2.
- **Screenshots:** 1280x800 (POS counter), 390x844 (Online on a phone).

## kitchen

- **Route:** `/kitchen`. Users: kitchen staff, on a tablet or a wall screen.
- **Specified in:** 01 section 5 (Flow A), table 3.2, section 8 (the two Kitchen rows), section 10 (Kitchen rejection reasons); 02 section 4 (the red warning), section 6 (the three buttons and their 409).
- **APIs:** `GET /tickets`, `POST /tickets/{order_id}/start`, `POST /tickets/{order_id}/reject`, `POST /tickets/{order_id}/complete`, `GET /alerts` of the Kitchen.
- **Must handle:**
  - two columns, Queued and Cooking; Completed, Cancelled and Failed tickets are not on this screen;
  - the red warning on a Queued ticket with a flagged ingredient, naming the ingredient;
  - Start cooking and Reject only on Queued, Complete only on Cooking;
  - 409 on any button: the ticket changed under the user (BR7). Reload it and show a short notice, not an error;
  - the reject dialog: a reason from the Kitchen-rejection group; "Spoiled ingredient" requires choosing at least one ingredient of that ticket; show the 400 if the service rejects the choice;
  - the wrong-branch cancel alerts (`HUY_SAI_CHI_NHANH`) and the "needs review" alerts.
- **Built in:** step 6b.
- **Screenshots:** 1024x768 (tablet, landscape), 1920x1080 (wall screen).

## inventory

- **Route:** `/inventory`. Users: the store keeper.
- **Specified in:** 01 section 3.3 (the stock accounting part), BR6, section 8 (the two Inventory rows); 02 section 3, section 6 and the notes on `clear-check` and `receipts`.
- **APIs:** `GET /stock`, `POST /stock/receipts`, `POST /ingredients/{id}/clear-check`, `GET /alerts` of Inventory.
- **Must handle:**
  - the four quantities per ingredient and the stock-check flag; flagged ingredients listed first;
  - a stock receipt for one ingredient;
  - clearing the flag, with the optional counted on-hand stock; the 409 when it is below the reserved quantity, with what the user must do (reject the tickets still holding it, 02 section 6);
  - the unmatched-command alerts (`LENH_KHONG_KHOP`) and the "needs review" alerts.
- **Built in:** step 6b.
- **Screenshots:** 1280x800.

## monitor

- **Route:** `/monitor`. Users: the operator.
- **Specified in:** 01 section 8 (every row), section 9 (the table on bad messages), section 15 (no close-order operation); 02 section 6, `GET /monitor` and `GET /alerts`.
- **APIs:** `GET /monitor` of Inventory, the Kitchen and each branch; `GET /alerts` of Inventory and the Kitchen.
- **Must handle:**
  - one row per service with its state; a service that does not answer is shown as down, the rest of the page still works;
  - the slow-consumer warning per topic;
  - the alerts of every kind, filterable by kind;
  - no action that changes an order's status (01 section 8, first paragraph).
- **Built in:** step 6b.
- **Screenshots:** 1280x800.

## reports

- **Route:** `/reports`. Users: Management.
- **Specified in:** 01 section 8 (the Management row and the paragraph below the table), section 14; 02 section 5 (replication and "data as of"), section 6 (`GET /reports/summary`).
- **APIs:** `GET /reports/summary`.
- **Must handle:**
  - "data as of hh:mm:ss" per branch, and a branch whose time has stopped moving (scenario 55);
  - order counts by status, and by reason for Cancelled and Failed;
  - a Cancel-pending record at the Kitchen is not counted, so the report does not claim to show it.
- **Built in:** step 7.
- **Screenshots:** 1280x800.

## demo

- **Route:** `/demo/:branchId`. Users: whoever presents the demo.
- **What it is:** the branch screen and the Kitchen screen side by side, so a race (scenario 3) or a cancel that arrives before the order (scenario 1) can be shown live. It reuses the two screens' components and adds no state of its own.
- **Built in:** step 6b, after `branch` and `kitchen`.
- **Screenshots:** 1920x1080.
