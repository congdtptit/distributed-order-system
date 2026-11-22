// The Inventory service's APIs (section 6 of docs/02-detailed-design.md), typed from its
// generated OpenAPI document. Quantities travel as decimal strings to stay exact.

import type { components } from "./generated/inventory";
import { call } from "./http";

export type StockItem = components["schemas"]["StockItem"];
export type InventoryAlert = components["schemas"]["Alert"];
export type InventoryMonitor = components["schemas"]["Monitor"];

const base = "/api/inventory";

export const inventoryApi = {
  stock: async () => (await call<StockItem[]>(`${base}/stock`)).body,
  alerts: async () => (await call<InventoryAlert[]>(`${base}/alerts`)).body,
  monitor: async () => (await call<InventoryMonitor>(`${base}/monitor`)).body,
  /** 404 (no such ingredient) and 422 (quantity not above 0) throw ApiError. */
  receive: async (ingredientId: string, quantity: string) =>
    (
      await call<StockItem>(`${base}/stock/receipts`, {
        method: "POST",
        body: JSON.stringify({ ingredient_id: ingredientId, quantity }),
      })
    ).body,
  /** 404, 409 (counted below reserved) and 422 throw ApiError. */
  clearCheck: async (ingredientId: string, countedOnHand: string | null) =>
    (
      await call<StockItem>(`${base}/ingredients/${ingredientId}/clear-check`, {
        method: "POST",
        body: JSON.stringify(countedOnHand === null ? {} : { counted_on_hand: countedOnHand }),
      })
    ).body,
};

/** "39", "0,15" in Vietnamese notation, at most 3 decimals (NUMERIC(12,3)). */
export function amount(value: string): string {
  return Number(value).toLocaleString("vi-VN", { maximumFractionDigits: 3 });
}
