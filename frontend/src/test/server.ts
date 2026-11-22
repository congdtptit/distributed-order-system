// MSW stands in for the services in the screen tests; handlers use the generated API types.
// Each test adds the responses it needs with ``server.use``; these defaults answer with empty
// data so that a screen renders.

import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import type { Monitor, Order } from "../api/branch";

export const EMPTY_MONITOR: Monitor = {
  connection: { connected: true, checked_at: "2026-11-20T09:15:00Z" },
  waiting_to_send: 0,
  awaiting_inventory: [],
  about_to_expire: [],
  cancel_requested: [],
  message_alerts: { count: 0, latest: [] },
};

export const server = setupServer(
  http.get("*/api/kitchen/tickets", () => HttpResponse.json([])),
  http.get("*/api/kitchen/alerts", () => HttpResponse.json([])),
  http.get("*/api/inventory/stock", () => HttpResponse.json([])),
  http.get("*/api/inventory/alerts", () => HttpResponse.json([])),
  http.get("*/api/:branch/orders", () => HttpResponse.json<Order[]>([])),
  http.get("*/api/:branch/monitor", () => HttpResponse.json(EMPTY_MONITOR)),
  http.get("*/api/:branch/dishes", () =>
    HttpResponse.json([
      { dish_id: "PHO_BO", name: "Phở bò" },
      { dish_id: "TRA_DA", name: "Trà đá" },
    ]),
  ),
);
