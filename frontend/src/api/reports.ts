// The Order Query Service's API (section 6 of docs/02-detailed-design.md): Management's report,
// read from the Central Order Replica. Typed from its generated OpenAPI document.

import type { components } from "./generated/reports";
import { call } from "./http";

export type Summary = components["schemas"]["Summary"];
export type BranchSummary = components["schemas"]["BranchSummary"];
export type ReasonCount = components["schemas"]["ReasonCount"];

export const reportsApi = {
  summary: async () => (await call<Summary>("/api/reports/reports/summary")).body,
};
