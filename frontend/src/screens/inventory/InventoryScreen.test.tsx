// The Inventory screen: one test per row of the state table (.claude/skills/screen/SKILL.md,
// step 1). The Inventory service is stubbed by MSW with the generated API types.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, HttpResponse, http } from "msw";
import type { InventoryAlert, StockItem } from "../../api/inventory";
import { renderRoute } from "../../test/render";
import { server } from "../../test/server";

function item(fields: Partial<StockItem> = {}): StockItem {
  return {
    ingredient_id: "BANH_PHO",
    name: "Bánh phở",
    unit: "kg",
    available: "10.000",
    reserved: "2.000",
    consumed: "0.400",
    wasted: "0.000",
    needs_check: false,
    ...fields,
  };
}

const MEAT = item({
  ingredient_id: "THIT_BO",
  name: "Thịt bò",
  available: "5.350",
  reserved: "1.500",
  consumed: "0.000",
  wasted: "0.150",
  needs_check: true,
});

function withStock(...items: StockItem[]) {
  server.use(http.get("*/api/inventory/stock", () => HttpResponse.json(items)));
}

async function rowOf(name: string) {
  const cell = await screen.findByText(name, { selector: "td *, td" });
  const row = cell.closest("tr");
  if (!row) throw new Error(`${name} is not in a table row`);
  return within(row);
}

describe("inventory screen: loading and service state", () => {
  it("shows a loader on the first load", async () => {
    server.use(
      http.get("*/api/inventory/stock", async () => {
        await delay("infinite");
        return HttpResponse.json([]);
      }),
    );
    renderRoute("/inventory");
    expect(await screen.findByLabelText("Đang tải tồn kho")).toBeInTheDocument();
  });

  it("explains an empty stock list", async () => {
    renderRoute("/inventory");
    expect(await screen.findByText(/Chưa có nguyên liệu nào/)).toBeInTheDocument();
  });

  it("shows a banner when Inventory does not answer and keeps the last data", async () => {
    withStock(item());
    const { client } = renderRoute("/inventory");
    await rowOf("Bánh phở");
    server.use(http.get("*/api/inventory/stock", () => HttpResponse.error()));
    await client.refetchQueries({ queryKey: ["inventory", "stock"] });
    expect(await screen.findByText("Không kết nối được tới Kho")).toBeInTheDocument();
    expect(screen.getByText("Bánh phở")).toBeInTheDocument();
  });
});

describe("inventory screen: stock", () => {
  it("shows the four quantities with the unit and the flag, flagged ingredients first", async () => {
    withStock(item(), MEAT);
    renderRoute("/inventory");
    const meat = await rowOf("Thịt bò");
    expect(meat.getByText("Chờ kiểm kho")).toBeInTheDocument();
    for (const value of ["5,35 kg", "1,5 kg", "0 kg", "0,15 kg"]) {
      expect(meat.getByText(value)).toBeInTheDocument();
    }
    const names = screen
      .getAllByRole("row")
      .slice(1)
      .map((r) => within(r).getAllByRole("cell")[0]?.textContent);
    expect(names[0]).toContain("Thịt bò");
    expect((await rowOf("Bánh phở")).queryByText("Chờ kiểm kho")).not.toBeInTheDocument();
  });

  it("receives stock for one ingredient (200)", async () => {
    withStock(item());
    let sent: unknown = null;
    server.use(
      http.post("*/api/inventory/stock/receipts", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(item({ available: "12.500" }));
      }),
    );
    renderRoute("/inventory");
    await userEvent.click((await rowOf("Bánh phở")).getByRole("button", { name: "Nhập kho" }));
    const dialog = await screen.findByRole("dialog", { name: /Nhập kho Bánh phở/ });
    await userEvent.type(
      within(dialog).getByRole("textbox", { name: "Số lượng nhập (kg)" }),
      "2.5",
    );
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận nhập kho" }));
    expect(await screen.findByText("Đã nhập 2,5 kg Bánh phở")).toBeInTheDocument();
    expect(sent).toEqual({ ingredient_id: "BANH_PHO", quantity: "2.5" });
  });

  it("shows a refused receipt quantity (422) under the field", async () => {
    withStock(item());
    server.use(
      http.post("*/api/inventory/stock/receipts", () =>
        HttpResponse.json(
          { detail: [{ loc: ["body", "quantity"], msg: "too many digits", type: "x" }] },
          { status: 422 },
        ),
      ),
    );
    renderRoute("/inventory");
    await userEvent.click((await rowOf("Bánh phở")).getByRole("button", { name: "Nhập kho" }));
    const dialog = await screen.findByRole("dialog", { name: /Nhập kho Bánh phở/ });
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Số lượng nhập (kg)" }), "1");
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận nhập kho" }));
    expect(await within(dialog).findByText(/Số lượng không hợp lệ/)).toBeInTheDocument();
  });

  it("says when the ingredient does not exist (404)", async () => {
    withStock(item());
    server.use(
      http.post("*/api/inventory/stock/receipts", () =>
        HttpResponse.json({ detail: "no ingredient BANH_PHO" }, { status: 404 }),
      ),
    );
    renderRoute("/inventory");
    await userEvent.click((await rowOf("Bánh phở")).getByRole("button", { name: "Nhập kho" }));
    const dialog = await screen.findByRole("dialog", { name: /Nhập kho Bánh phở/ });
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Số lượng nhập (kg)" }), "1");
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận nhập kho" }));
    expect(await screen.findByText("Kho không có nguyên liệu này, đã tải lại")).toBeInTheDocument();
  });

  it("offers clearing the flag only on a flagged ingredient", async () => {
    withStock(item(), MEAT);
    renderRoute("/inventory");
    expect(
      (await rowOf("Thịt bò")).getByRole("button", { name: "Kiểm kho xong" }),
    ).toBeInTheDocument();
    expect(
      (await rowOf("Bánh phở")).queryByRole("button", { name: "Kiểm kho xong" }),
    ).not.toBeInTheDocument();
  });

  it("clears the flag with the counted on-hand stock (200)", async () => {
    withStock(MEAT);
    let sent: unknown = null;
    server.use(
      http.post("*/api/inventory/ingredients/:id/clear-check", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ...MEAT, needs_check: false });
      }),
    );
    renderRoute("/inventory");
    await userEvent.click((await rowOf("Thịt bò")).getByRole("button", { name: "Kiểm kho xong" }));
    const dialog = await screen.findByRole("dialog", { name: /Kiểm kho xong: Thịt bò/ });
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Tồn đếm được (kg)" }), "6");
    await userEvent.click(within(dialog).getByRole("button", { name: "Gỡ cờ kiểm kho" }));
    expect(await screen.findByText("Đã gỡ cờ kiểm kho của Thịt bò")).toBeInTheDocument();
    expect(sent).toEqual({ counted_on_hand: "6" });
  });

  it("clears the flag without a count (available unchanged)", async () => {
    withStock(MEAT);
    let sent: unknown = null;
    server.use(
      http.post("*/api/inventory/ingredients/:id/clear-check", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ...MEAT, needs_check: false });
      }),
    );
    renderRoute("/inventory");
    await userEvent.click((await rowOf("Thịt bò")).getByRole("button", { name: "Kiểm kho xong" }));
    const dialog = await screen.findByRole("dialog", { name: /Kiểm kho xong: Thịt bò/ });
    await userEvent.click(within(dialog).getByRole("button", { name: "Gỡ cờ kiểm kho" }));
    expect(await screen.findByText("Đã gỡ cờ kiểm kho của Thịt bò")).toBeInTheDocument();
    expect(sent).toEqual({});
  });

  it("explains a count below the reserved quantity (409) and what to do", async () => {
    withStock(MEAT);
    server.use(
      http.post("*/api/inventory/ingredients/:id/clear-check", () =>
        HttpResponse.json(
          { detail: { message: "below reserved", reserved: "1.500" } },
          { status: 409 },
        ),
      ),
    );
    renderRoute("/inventory");
    await userEvent.click((await rowOf("Thịt bò")).getByRole("button", { name: "Kiểm kho xong" }));
    const dialog = await screen.findByRole("dialog", { name: /Kiểm kho xong: Thịt bò/ });
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Tồn đếm được (kg)" }), "1");
    await userEvent.click(within(dialog).getByRole("button", { name: "Gỡ cờ kiểm kho" }));
    const message = await within(dialog).findByRole("alert");
    expect(message).toHaveTextContent("ít hơn lượng đang giữ 1,5 kg");
    expect(message).toHaveTextContent("từ chối các phiếu còn giữ Thịt bò");
  });

  it("announces a flag change in the live region", async () => {
    withStock(MEAT);
    const { client } = renderRoute("/inventory");
    await rowOf("Thịt bò");
    withStock({ ...MEAT, needs_check: false });
    await client.refetchQueries({ queryKey: ["inventory", "stock"] });
    expect(await screen.findByText("Thịt bò đã được gỡ cờ kiểm kho")).toBeInTheDocument();
  });
});

describe("inventory screen: alerts", () => {
  it("lists unmatched commands and orders that need review", async () => {
    const alerts: InventoryAlert[] = [
      {
        id: 2,
        kind: "LENH_KHONG_KHOP",
        order_id: "a41f0c2e-1111-4222-8333-444455556666",
        event_id: null,
        source_topic: "stock-commands",
        source_partition: 0,
        source_offset: 3,
        detail: { event_type: "ReleaseRequested", record_status: null },
        created_at: "2026-11-20T09:20:00Z",
      },
      {
        id: 1,
        kind: "CAN_KIEM_TRA",
        order_id: null,
        event_id: null,
        source_topic: "order-events.POS01",
        source_partition: 1,
        source_offset: 9,
        detail: { error: "UnreadableMessage" },
        created_at: "2026-11-20T09:18:00Z",
      },
    ];
    server.use(http.get("*/api/inventory/alerts", () => HttpResponse.json(alerts)));
    renderRoute("/inventory");
    const region = within(await screen.findByRole("region", { name: "Cảnh báo của Kho" }));
    expect(region.getByText(/Lệnh không khớp/)).toBeInTheDocument();
    expect(region.getByText(/ReleaseRequested cho đơn không có bản ghi/)).toBeInTheDocument();
    expect(region.getByText(/Cần kiểm tra/)).toBeInTheDocument();
  });
});
