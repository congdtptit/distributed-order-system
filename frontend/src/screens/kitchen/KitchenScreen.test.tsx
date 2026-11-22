// The Kitchen screen: one test per row of the state table (.claude/skills/screen/SKILL.md,
// step 1). The Kitchen service is stubbed by MSW with the generated API types.

import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, HttpResponse, http } from "msw";
import type { Alert, Ticket } from "../../api/kitchen";
import { renderRoute } from "../../test/render";
import { server } from "../../test/server";

const ID = "a41f0c2e-1111-4222-8333-444455556666";
const COOKING_ID = "b52e0000-1111-4222-8333-444455556666";

function ticket(fields: Partial<Ticket> = {}): Ticket {
  return {
    order_id: ID,
    status: "CHO_NAU",
    origin_branch: "POS01",
    order_created_at: "2026-11-20T09:15:00Z",
    items: [{ dish_id: "PHO_BO", name: "Phở bò", quantity: 2 }],
    reserved: [
      { ingredient_id: "BANH_PHO", name: "Bánh phở", unit: "kg", quantity: 0.4 },
      { ingredient_id: "THIT_BO", name: "Thịt bò", unit: "kg", quantity: 0.3 },
    ],
    warnings: [],
    ...fields,
  };
}

function withTickets(...tickets: Ticket[]) {
  server.use(http.get("*/api/kitchen/tickets", () => HttpResponse.json(tickets)));
}

function withAlerts(...alerts: Alert[]) {
  server.use(http.get("*/api/kitchen/alerts", () => HttpResponse.json(alerts)));
}

async function cardOf(id: string = ID) {
  const label = await screen.findByText(id.slice(0, 8), { selector: "span" });
  const card = label.closest("[data-ticket]");
  if (!(card instanceof HTMLElement)) throw new Error("the ticket is not in a card");
  return within(card);
}

function column(name: string) {
  return within(screen.getByRole("region", { name }));
}

async function openReject() {
  const card = await cardOf();
  await userEvent.click(card.getByRole("button", { name: "Từ chối" }));
  return screen.findByRole("dialog", { name: /Từ chối phiếu/ });
}

async function chooseReason(dialog: HTMLElement, label: string) {
  await userEvent.click(within(dialog).getByRole("combobox", { name: "Lý do từ chối" }));
  await userEvent.click(await screen.findByRole("option", { name: label }));
}

describe("kitchen screen: loading and service state", () => {
  it("shows a loader on the first load", async () => {
    server.use(
      http.get("*/api/kitchen/tickets", async () => {
        await delay("infinite");
        return HttpResponse.json([]);
      }),
    );
    renderRoute("/kitchen");
    expect(await screen.findByLabelText("Đang tải phiếu")).toBeInTheDocument();
  });

  it("explains empty columns", async () => {
    renderRoute("/kitchen");
    expect(await screen.findByText(/Chưa có phiếu nào đang chờ nấu/)).toBeInTheDocument();
    expect(screen.getByText(/Chưa có phiếu nào đang nấu/)).toBeInTheDocument();
  });

  it("shows a banner when the Kitchen does not answer and keeps the last data", async () => {
    withTickets(ticket());
    const { client } = renderRoute("/kitchen");
    await cardOf();
    server.use(http.get("*/api/kitchen/tickets", () => HttpResponse.error()));
    await client.refetchQueries({ queryKey: ["kitchen", "tickets"] });
    expect(await screen.findByText("Không kết nối được tới Bếp")).toBeInTheDocument();
    expect(screen.getByText(ID.slice(0, 8), { selector: "span" })).toBeInTheDocument();
  });
});

describe("kitchen screen: tickets", () => {
  it("puts Queued and Cooking tickets in their columns with their details", async () => {
    withTickets(ticket(), ticket({ order_id: COOKING_ID, status: "DANG_NAU" }));
    renderRoute("/kitchen");
    await cardOf();
    expect(column("Chờ nấu").getByText(ID.slice(0, 8), { selector: "span" })).toBeInTheDocument();
    expect(
      column("Đang nấu").getByText(COOKING_ID.slice(0, 8), { selector: "span" }),
    ).toBeInTheDocument();
    const card = await cardOf();
    expect(card.getByText("Phở bò ×2")).toBeInTheDocument();
    expect(card.getByText(/POS01/)).toBeInTheDocument();
    expect(card.getByText(/Thịt bò 0,3 kg/)).toBeInTheDocument();
  });

  it("shows the red warning naming the flagged ingredient", async () => {
    withTickets(ticket({ warnings: ["THIT_BO"] }));
    renderRoute("/kitchen");
    const card = await cardOf();
    expect(card.getByRole("alert")).toHaveTextContent("Thịt bò đang chờ kiểm kho");
  });

  it("offers Start cooking and Reject on Queued, Complete only on Cooking", async () => {
    withTickets(ticket(), ticket({ order_id: COOKING_ID, status: "DANG_NAU" }));
    renderRoute("/kitchen");
    const queued = await cardOf();
    expect(queued.getByRole("button", { name: "Bắt đầu nấu" })).toBeInTheDocument();
    expect(queued.getByRole("button", { name: "Từ chối" })).toBeInTheDocument();
    expect(queued.queryByRole("button", { name: "Hoàn tất" })).not.toBeInTheDocument();
    const cooking = await cardOf(COOKING_ID);
    expect(cooking.getByRole("button", { name: "Hoàn tất" })).toBeInTheDocument();
    expect(cooking.queryByRole("button", { name: "Bắt đầu nấu" })).not.toBeInTheDocument();
    expect(cooking.queryByRole("button", { name: "Từ chối" })).not.toBeInTheDocument();
  });

  it("starts cooking (200)", async () => {
    withTickets(ticket());
    server.use(
      http.post("*/api/kitchen/tickets/:id/start", () =>
        HttpResponse.json(ticket({ status: "DANG_NAU" })),
      ),
    );
    renderRoute("/kitchen");
    await userEvent.click((await cardOf()).getByRole("button", { name: "Bắt đầu nấu" }));
    expect(await screen.findByText(`Phiếu ${ID.slice(0, 8)} đang nấu`)).toBeInTheDocument();
  });

  it("completes a Cooking ticket (200)", async () => {
    withTickets(ticket({ status: "DANG_NAU" }));
    server.use(
      http.post("*/api/kitchen/tickets/:id/complete", () =>
        HttpResponse.json(ticket({ status: "HOAN_TAT" })),
      ),
    );
    renderRoute("/kitchen");
    await userEvent.click((await cardOf()).getByRole("button", { name: "Hoàn tất" }));
    expect(await screen.findByText(`Phiếu ${ID.slice(0, 8)} đã hoàn tất`)).toBeInTheDocument();
  });

  it.each([
    ["start", "Bắt đầu nấu"],
    ["complete", "Hoàn tất"],
  ])("treats 409 on %s as a notice and reloads", async (action, button) => {
    let reads = 0;
    server.use(
      http.get("*/api/kitchen/tickets", () => {
        reads += 1;
        return HttpResponse.json([ticket({ status: action === "start" ? "CHO_NAU" : "DANG_NAU" })]);
      }),
      http.post(`*/api/kitchen/tickets/:id/${action}`, () =>
        HttpResponse.json({ detail: { message: "changed", status: "DA_HUY" } }, { status: 409 }),
      ),
    );
    renderRoute("/kitchen");
    const card = await cardOf();
    const before = reads;
    await userEvent.click(card.getByRole("button", { name: button }));
    expect(await screen.findByText("Phiếu vừa đổi trạng thái, đã tải lại")).toBeInTheDocument();
    await waitFor(() => expect(reads).toBeGreaterThan(before));
  });

  it("announces a ticket's status change in the live region", async () => {
    withTickets(ticket());
    const { client } = renderRoute("/kitchen");
    await cardOf();
    withTickets(ticket({ status: "DANG_NAU" }));
    await client.refetchQueries({ queryKey: ["kitchen", "tickets"] });
    expect(
      await screen.findByText(`Phiếu ${ID.slice(0, 8)} đã chuyển sang Đang nấu`),
    ).toBeInTheDocument();
  });
});

describe("kitchen screen: rejecting", () => {
  it("requires a reason from the Kitchen-rejection group", async () => {
    withTickets(ticket());
    renderRoute("/kitchen");
    const dialog = await openReject();
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận từ chối" }));
    expect(await within(dialog).findByText("Chọn lý do từ chối")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("combobox", { name: "Lý do từ chối" }));
    const options = (await screen.findAllByRole("option")).map((o) => o.textContent);
    expect(options).toEqual(["Hỏng thiết bị", "Thiếu nhân viên", "Nguyên liệu hỏng"]);
  });

  it("requires a spoiled ingredient of this ticket for the reason Spoiled ingredient", async () => {
    withTickets(ticket());
    let sent: unknown = null;
    server.use(
      http.post("*/api/kitchen/tickets/:id/reject", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(ticket({ status: "DA_HUY" }));
      }),
    );
    renderRoute("/kitchen");
    const dialog = await openReject();
    await chooseReason(dialog, "Nguyên liệu hỏng");
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận từ chối" }));
    expect(await within(dialog).findByText("Chọn nguyên liệu bị hỏng")).toBeInTheDocument();
    expect(sent).toBeNull();
    expect(within(dialog).getAllByRole("checkbox")).toHaveLength(2); // this ticket's ingredients
    await userEvent.click(within(dialog).getByRole("checkbox", { name: /Thịt bò/ }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận từ chối" }));
    expect(await screen.findByText(`Đã từ chối phiếu ${ID.slice(0, 8)}`)).toBeInTheDocument();
    expect(sent).toEqual({ reason_code: "SPOILED_INGREDIENT", spoiled_ingredients: ["THIT_BO"] });
  });

  it("rejects with another reason and no ingredients (200)", async () => {
    withTickets(ticket());
    let sent: unknown = null;
    server.use(
      http.post("*/api/kitchen/tickets/:id/reject", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(ticket({ status: "DA_HUY" }));
      }),
    );
    renderRoute("/kitchen");
    const dialog = await openReject();
    await chooseReason(dialog, "Thiếu nhân viên");
    expect(within(dialog).queryByRole("checkbox")).not.toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận từ chối" }));
    expect(await screen.findByText(`Đã từ chối phiếu ${ID.slice(0, 8)}`)).toBeInTheDocument();
    expect(sent).toEqual({ reason_code: "SHORT_STAFFED", spoiled_ingredients: [] });
  });

  it("shows the service's refusal (400) in the dialog", async () => {
    withTickets(ticket());
    server.use(
      http.post("*/api/kitchen/tickets/:id/reject", () =>
        HttpResponse.json({ detail: { message: "not on this ticket: ['X']" } }, { status: 400 }),
      ),
    );
    renderRoute("/kitchen");
    const dialog = await openReject();
    await chooseReason(dialog, "Hỏng thiết bị");
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận từ chối" }));
    expect(await within(dialog).findByText(/Bếp không nhận lựa chọn này/)).toBeInTheDocument();
  });

  it("treats 409 on reject as a notice and reloads", async () => {
    withTickets(ticket());
    server.use(
      http.post("*/api/kitchen/tickets/:id/reject", () =>
        HttpResponse.json({ detail: { message: "changed", status: "DANG_NAU" } }, { status: 409 }),
      ),
    );
    renderRoute("/kitchen");
    const dialog = await openReject();
    await chooseReason(dialog, "Hỏng thiết bị");
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận từ chối" }));
    expect(await screen.findByText("Phiếu vừa đổi trạng thái, đã tải lại")).toBeInTheDocument();
  });
});

describe("kitchen screen: alerts", () => {
  it("lists wrong-branch cancel requests and orders that need review", async () => {
    withAlerts(
      {
        id: 2,
        kind: "HUY_SAI_CHI_NHANH",
        order_id: ID,
        event_id: null,
        source_topic: "cancel-events.POS02",
        source_partition: 0,
        source_offset: 4,
        detail: { origin_branch: "POS01", dismissed: ["POS02"] },
        created_at: "2026-11-20T09:20:00Z",
      },
      {
        id: 1,
        kind: "CAN_KIEM_TRA",
        order_id: COOKING_ID,
        event_id: null,
        source_topic: "kitchen-orders",
        source_partition: 1,
        source_offset: 7,
        detail: { error: "UnreadableMessage" },
        created_at: "2026-11-20T09:18:00Z",
      },
    );
    renderRoute("/kitchen");
    const region = within(await screen.findByRole("region", { name: "Cảnh báo của Bếp" }));
    expect(region.getByText(/Hủy sai chi nhánh/)).toBeInTheDocument();
    expect(region.getByText(/gốc POS01, bỏ qua POS02/)).toBeInTheDocument();
    expect(region.getByText(/Cần kiểm tra/)).toBeInTheDocument();
  });

  it("shows a page of each column with the column's total, and loads more on request", async () => {
    const all = Array.from({ length: 25 }, (_, i) =>
      ticket({ order_id: `c0000000-0000-4000-8000-${String(i).padStart(12, "0")}` }),
    );
    server.use(
      http.get("*/api/kitchen/tickets", ({ request }) => {
        const limit = Number(new URL(request.url).searchParams.get("limit"));
        return HttpResponse.json(all.slice(0, limit));
      }),
      http.get("*/api/kitchen/tickets/counts", () =>
        HttpResponse.json({ CHO_NAU: 25, DANG_NAU: 0 }),
      ),
    );
    renderRoute("/kitchen");
    expect(await screen.findByRole("heading", { name: "Chờ nấu (25)" })).toBeInTheDocument();
    const queuedColumn = () => screen.getByRole("region", { name: "Chờ nấu" });
    expect(queuedColumn().querySelectorAll("[data-ticket]")).toHaveLength(20);
    await userEvent.click(
      column("Chờ nấu").getByRole("button", { name: "Xem thêm (còn 5 phiếu)" }),
    );
    await waitFor(() => expect(queuedColumn().querySelectorAll("[data-ticket]")).toHaveLength(25));
    expect(column("Chờ nấu").queryByRole("button", { name: /Xem thêm/ })).not.toBeInTheDocument();
  });
});
