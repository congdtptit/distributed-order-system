// The Kitchen service's APIs (section 6 of docs/02-detailed-design.md), typed from its
// generated OpenAPI document.

import type { components } from "./generated/kitchen";
import { call } from "./http";

export type Ticket = components["schemas"]["Ticket"];
export type Alert = components["schemas"]["Alert"];
export type Rejection = components["schemas"]["Rejection"];

const base = "/api/kitchen";

/** A ticket's ``items`` as Inventory passed them on: dish, name, quantity. */
export interface TicketItem {
  dish_id: string;
  name: string;
  quantity: number;
}

export function ticketItems(ticket: Ticket): TicketItem[] {
  return ticket.items.map((raw) => ({
    dish_id: String(raw.dish_id ?? ""),
    name: String(raw.name ?? raw.dish_id ?? ""),
    quantity: Number(raw.quantity ?? 0),
  }));
}

export const kitchenApi = {
  tickets: async () => (await call<Ticket[]>(`${base}/tickets`)).body,
  alerts: async () => (await call<Alert[]>(`${base}/alerts`)).body,
  /** 200 with the ticket; 404 and 409 throw ApiError. */
  start: async (orderId: string) =>
    (await call<Ticket>(`${base}/tickets/${orderId}/start`, { method: "POST" })).body,
  complete: async (orderId: string) =>
    (await call<Ticket>(`${base}/tickets/${orderId}/complete`, { method: "POST" })).body,
  /** 400 (reason or ingredients refused), 404 and 409 throw ApiError. */
  reject: async (orderId: string, rejection: Rejection) =>
    (
      await call<Ticket>(`${base}/tickets/${orderId}/reject`, {
        method: "POST",
        body: JSON.stringify(rejection),
      })
    ).body,
};
