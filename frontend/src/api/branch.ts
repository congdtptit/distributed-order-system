// The Branch service's APIs (section 6 of docs/02-detailed-design.md), typed from its generated
// OpenAPI document. One instance per branch: /api/pos01, /api/pos02, /api/online.

import type { components } from "./generated/branch";
import { call } from "./http";

export type Order = components["schemas"]["Order"];
export type Dish = components["schemas"]["Dish"];
export type Monitor = components["schemas"]["Monitor"];
export type NewOrder = components["schemas"]["NewOrder"];

export const BRANCHES = ["POS01", "POS02", "ONLINE"] as const;
export type BranchId = (typeof BRANCHES)[number];

export function isBranch(value: string | undefined): value is BranchId {
  return (BRANCHES as readonly string[]).includes(value ?? "");
}

export function branchApi(branch: BranchId) {
  const base = `/api/${branch.toLowerCase()}`;
  return {
    base,
    dishes: async () => (await call<Dish[]>(`${base}/dishes`)).body,
    orders: async () => (await call<Order[]>(`${base}/orders`)).body,
    monitor: async () => (await call<Monitor>(`${base}/monitor`)).body,
    place: async (order: NewOrder) =>
      (await call<Order>(`${base}/orders`, { method: "POST", body: JSON.stringify(order) })).body,
    /** 200: cancelled here; 202: the Kitchen decides. 400, 404 and 409 throw ApiError. */
    cancel: (orderId: string, reasonCode: string) =>
      call<Order>(`${base}/orders/${orderId}/cancel`, {
        method: "POST",
        body: JSON.stringify({ reason_code: reasonCode }),
      }),
  };
}
