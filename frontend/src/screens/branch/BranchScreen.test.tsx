// The branch screen: one test per row of the state table (.claude/skills/screen/SKILL.md,
// step 1). The services are stubbed by MSW with the generated API types.

import { focusManager } from "@tanstack/react-query";
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, HttpResponse, http } from "msw";
import type { Menu, Monitor, Order } from "../../api/branch";
import { renderRoute } from "../../test/render";
import { EMPTY_MONITOR, server } from "../../test/server";

const ID = "a41f0c2e-1111-4222-8333-444455556666";

function order(fields: Partial<Order> = {}): Order {
  return {
    order_id: ID,
    branch_id: "POS01",
    status: "CHO_KHO",
    close_reason: null,
    cancel_flag: "KHONG",
    cancel_requested_at: null,
    cancel_message: null,
    items: [{ dish_id: "PHO_BO", name: "Phở bò", quantity: 2 }],
    created_at: "2026-11-20T09:15:00Z",
    send_state: "CHUA_GUI",
    cancel_send_state: null,
    ...fields,
  };
}

function withOrders(...orders: Order[]) {
  server.use(http.get("*/api/pos01/orders", () => HttpResponse.json(orders)));
}

function withMonitor(fields: Partial<Monitor>) {
  server.use(
    http.get("*/api/pos01/monitor", () => HttpResponse.json({ ...EMPTY_MONITOR, ...fields })),
  );
}

function minutesAgo(minutes: number): string {
  return new Date(Date.now() - minutes * 60_000).toISOString();
}

async function rowOf(id: string = ID) {
  const cell = await screen.findByText(id.slice(0, 8), { selector: "span" });
  const row = cell.closest("tr");
  if (!row) throw new Error("the order is not in a table row");
  return within(row);
}

async function openCancel(id: string = ID) {
  const row = await rowOf(id);
  await userEvent.click(row.getByRole("button", { name: "Hủy đơn" }));
  return screen.findByRole("dialog", { name: /Hủy đơn/ });
}

async function chooseReason(dialog: HTMLElement, label: string) {
  await userEvent.click(within(dialog).getByRole("combobox", { name: "Lý do hủy" }));
  await userEvent.click(await screen.findByRole("option", { name: label }));
}

describe("branch screen: loading and service state", () => {
  it("shows a loader on the first load", async () => {
    server.use(
      http.get("*/api/pos01/orders", async () => {
        await delay("infinite");
        return HttpResponse.json([]);
      }),
    );
    renderRoute("/branch/POS01");
    expect(await screen.findByLabelText("Đang tải đơn")).toBeInTheDocument();
  });

  it("explains an empty order list", async () => {
    renderRoute("/branch/POS01");
    expect(await screen.findByText(/Chưa có đơn nào/)).toBeInTheDocument();
  });

  it("shows a banner when the branch service does not answer and keeps the last data", async () => {
    withOrders(order());
    const { client } = renderRoute("/branch/POS01");
    await rowOf();
    server.use(http.get("*/api/pos01/orders", () => HttpResponse.error()));
    await client.refetchQueries({ queryKey: ["branch", "POS01", "orders"] });
    expect(await screen.findByText("Không kết nối được tới chi nhánh POS01")).toBeInTheDocument();
    expect(screen.getByText(ID.slice(0, 8), { selector: "span" })).toBeInTheDocument();
  });
});

describe("branch screen: what each order shows", () => {
  it.each([
    ["CHO_KHO", "Chờ Kho"],
    ["DA_GIU", "Đã giữ"],
    ["HOAN_TAT", "Hoàn tất"],
    ["DA_HUY", "Đã hủy"],
    ["THAT_BAI", "Thất bại"],
  ])("shows status %s as the badge %s", async (status, label) => {
    withOrders(order({ status }));
    renderRoute("/branch/POS01");
    expect((await rowOf()).getByText(label)).toBeInTheDocument();
  });

  it("shows the reason of a Failed or Cancelled order", async () => {
    withOrders(order({ status: "THAT_BAI", close_reason: "ORDER_EXPIRED" }));
    renderRoute("/branch/POS01");
    expect((await rowOf()).getByText("Đơn quá hạn")).toBeInTheDocument();
  });

  it("shows the cancel flag: pending with the time waited, kitchen will not cook, none", async () => {
    withOrders(
      order({ cancel_flag: "DANG_YEU_CAU", cancel_requested_at: minutesAgo(3) }),
      order({ order_id: "b52e0000-1111-4222-8333-444455556666", cancel_flag: "BEP_KHONG_NAU" }),
      order({ order_id: "c63f0000-1111-4222-8333-444455556666" }),
    );
    renderRoute("/branch/POS01");
    expect((await rowOf()).getByText(/Đang yêu cầu hủy · 3 phút/)).toBeInTheDocument();
    expect((await rowOf("b52e0000")).getByText("Bếp sẽ không nấu")).toBeInTheDocument();
    const plain = await rowOf("c63f0000");
    expect(plain.queryByText(/yêu cầu hủy|không nấu/)).not.toBeInTheDocument();
  });

  it("shows the kitchen's refusal in Vietnamese", async () => {
    withOrders(
      order({ status: "DA_GIU", cancel_message: "Cannot cancel: the kitchen has started cooking" }),
    );
    renderRoute("/branch/POS01");
    expect((await rowOf()).getByText("Không hủy được: bếp đã bắt đầu nấu")).toBeInTheDocument();
  });

  it.each([
    ["CHUA_GUI", "Chưa gửi, bếp chưa nhận"],
    ["DANG_GUI", "Đang gửi, chưa biết bếp đã nhận chưa"],
  ])("shows the send state %s as BR5 words it", async (state, text) => {
    withOrders(order({ send_state: state }));
    renderRoute("/branch/POS01");
    expect((await rowOf()).getByText(text)).toBeInTheDocument();
  });

  it("says a cancel request not yet sent is no guarantee", async () => {
    withOrders(
      order({
        send_state: "DA_GUI",
        cancel_flag: "DANG_YEU_CAU",
        cancel_requested_at: minutesAgo(1),
        cancel_send_state: "CHUA_GUI",
      }),
    );
    renderRoute("/branch/POS01");
    expect(
      (await rowOf()).getByText("Chưa gửi yêu cầu hủy, chưa chắc hủy được"),
    ).toBeInTheDocument();
  });

  it.each(["HOAN_TAT", "DA_HUY", "THAT_BAI"])(
    "hides Cancel for a terminal order (%s)",
    async (status) => {
      withOrders(order({ status }));
      renderRoute("/branch/POS01");
      expect((await rowOf()).queryByRole("button", { name: "Hủy đơn" })).not.toBeInTheDocument();
    },
  );

  it("offers no second cancel while a request is pending", async () => {
    withOrders(order({ cancel_flag: "DANG_YEU_CAU", cancel_requested_at: minutesAgo(1) }));
    renderRoute("/branch/POS01");
    expect((await rowOf()).queryByRole("button", { name: "Hủy đơn" })).not.toBeInTheDocument();
  });

  it("announces a status change in the live region", async () => {
    withOrders(order());
    const { client } = renderRoute("/branch/POS01");
    await rowOf();
    withOrders(order({ status: "DA_GIU" }));
    await client.refetchQueries({ queryKey: ["branch", "POS01", "orders"] });
    expect(
      await screen.findByText(`Đơn ${ID.slice(0, 8)} đã chuyển sang Đã giữ`),
    ).toBeInTheDocument();
  });
});

describe("branch screen: cancelling", () => {
  it("requires a reason from the customer-cancel group", async () => {
    withOrders(order());
    renderRoute("/branch/POS01");
    const dialog = await openCancel();
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận hủy" }));
    expect(await within(dialog).findByText("Chọn lý do hủy")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("combobox", { name: "Lý do hủy" }));
    const options = (await screen.findAllByRole("option")).map((o) => o.textContent);
    expect(options).toEqual(["Khách đổi ý", "Đợi quá lâu", "Nhập nhầm đơn"]);
  });

  it("reports a local cancel (200)", async () => {
    withOrders(order());
    let sent: unknown = null;
    server.use(
      http.post("*/api/pos01/orders/:id/cancel", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(order({ status: "DA_HUY", send_state: null }), { status: 200 });
      }),
    );
    renderRoute("/branch/POS01");
    const dialog = await openCancel();
    await chooseReason(dialog, "Khách đổi ý");
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận hủy" }));
    expect(
      await screen.findByText(`Đã hủy đơn ${ID.slice(0, 8)} tại chi nhánh`),
    ).toBeInTheDocument();
    expect(sent).toEqual({ reason_code: "CHANGED_MIND" });
  });

  it("reports a request sent to the Kitchen (202), which is no guarantee", async () => {
    withOrders(order({ send_state: "DA_GUI" }));
    server.use(
      http.post("*/api/pos01/orders/:id/cancel", () =>
        HttpResponse.json(order({ cancel_flag: "DANG_YEU_CAU" }), { status: 202 }),
      ),
    );
    renderRoute("/branch/POS01");
    const dialog = await openCancel();
    await chooseReason(dialog, "Đợi quá lâu");
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận hủy" }));
    expect(
      await screen.findByText(
        `Đã gửi yêu cầu hủy đơn ${ID.slice(0, 8)} tới Bếp. Bếp quyết định: chưa chắc hủy được.`,
      ),
    ).toBeInTheDocument();
  });

  it("treats 409 as a notice and reloads", async () => {
    let reads = 0;
    server.use(
      http.get("*/api/pos01/orders", () => {
        reads += 1;
        return HttpResponse.json([order()]);
      }),
      http.post("*/api/pos01/orders/:id/cancel", () =>
        HttpResponse.json(
          { detail: { message: "the order is already HOAN_TAT", status: "HOAN_TAT" } },
          { status: 409 },
        ),
      ),
    );
    renderRoute("/branch/POS01");
    const dialog = await openCancel();
    await chooseReason(dialog, "Khách đổi ý");
    const before = reads;
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận hủy" }));
    expect(await screen.findByText("Đơn vừa đổi trạng thái, đã tải lại")).toBeInTheDocument();
    await waitFor(() => expect(reads).toBeGreaterThan(before));
  });

  it("says when the order does not exist (404)", async () => {
    withOrders(order());
    server.use(
      http.post("*/api/pos01/orders/:id/cancel", () =>
        HttpResponse.json({ detail: { message: "no such order" } }, { status: 404 }),
      ),
    );
    renderRoute("/branch/POS01");
    const dialog = await openCancel();
    await chooseReason(dialog, "Khách đổi ý");
    await userEvent.click(within(dialog).getByRole("button", { name: "Xác nhận hủy" }));
    expect(await screen.findByText("Không tìm thấy đơn này ở chi nhánh")).toBeInTheDocument();
  });
});

describe("branch screen: placing an order", () => {
  it("lists the dishes and places an order (201)", async () => {
    let sent: unknown = null;
    server.use(
      http.post("*/api/pos01/orders", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(order(), { status: 201 });
      }),
    );
    renderRoute("/branch/POS01");
    const pho = await screen.findByRole("textbox", { name: "Phở bò" });
    await userEvent.type(pho, "2");
    await userEvent.click(screen.getByRole("button", { name: "Tạo đơn" }));
    expect(
      await screen.findByText(`Đã tạo đơn ${ID.slice(0, 8)}, đang chờ Kho`),
    ).toBeInTheDocument();
    expect(sent).toEqual({ items: [{ dish_id: "PHO_BO", quantity: 2 }] });
  });

  it("shows a refused order (400) next to the form", async () => {
    server.use(
      http.post("*/api/pos01/orders", () =>
        HttpResponse.json({ detail: { message: "unknown dish: PHO_BO" } }, { status: 400 }),
      ),
    );
    renderRoute("/branch/POS01");
    await userEvent.type(await screen.findByRole("textbox", { name: "Phở bò" }), "1");
    await userEvent.click(screen.getByRole("button", { name: "Tạo đơn" }));
    expect(await screen.findByText(/Đơn không hợp lệ/)).toBeInTheDocument();
  });
});

describe("branch screen: Flow D", () => {
  it("shows the connection to Kafka and the entries waiting to be sent", async () => {
    withMonitor({
      connection: { connected: false, checked_at: minutesAgo(0) },
      waiting_to_send: 3,
    });
    renderRoute("/branch/POS01");
    expect(await screen.findByText("Mất kết nối Kafka")).toBeInTheDocument();
    expect(screen.getByText("3 mục chờ gửi")).toBeInTheDocument();
  });

  it("alerts an order awaiting Inventory too long, with a Request cancellation button", async () => {
    withOrders(order({ send_state: "DA_GUI" }));
    withMonitor({
      awaiting_inventory: [
        { order_id: ID, created_at: minutesAgo(11), waited_s: 660, cancel_flag: "KHONG" },
      ],
    });
    renderRoute("/branch/POS01");
    const alert = await screen.findByRole("alert", { name: /Đơn chờ Kho quá lâu/ });
    expect(within(alert).getByText(/đã chờ 11 phút/)).toBeInTheDocument();
    await userEvent.click(within(alert).getByRole("button", { name: "Yêu cầu hủy" }));
    expect(await screen.findByRole("dialog", { name: /Hủy đơn/ })).toBeInTheDocument();
  });

  it("alerts an order about to pass the X-hour limit", async () => {
    withMonitor({
      about_to_expire: [
        {
          order_id: ID,
          created_at: minutesAgo(190),
          expires_at: new Date(Date.now() + 50 * 60_000).toISOString(),
        },
      ],
    });
    renderRoute("/branch/POS01");
    const alert = await screen.findByRole("alert", { name: /Đơn sắp quá hạn/ });
    expect(within(alert).getByText(/hết hạn lúc/)).toBeInTheDocument();
  });

  it("alerts status messages the branch could not read or recognise", async () => {
    withMonitor({
      message_alerts: {
        count: 1,
        latest: [
          {
            kind: "CAN_KIEM_TRA",
            order_id: ID,
            event_id: null,
            source_topic: "status-events.POS01",
            detail: { error: "unknown event_type 'X'" },
            created_at: minutesAgo(2),
          },
        ],
      },
    });
    renderRoute("/branch/POS01");
    expect(
      await screen.findByText("1 tin trạng thái không đọc được hoặc không nhận ra"),
    ).toBeInTheDocument();
  });

  it("lists a page of the newest orders and loads older ones on request", async () => {
    const all = Array.from({ length: 30 }, (_, i) =>
      order({ order_id: `d0000000-0000-4000-8000-${String(i).padStart(12, "0")}` }),
    );
    let asked = 0;
    server.use(
      http.get("*/api/pos01/orders", ({ request }) => {
        asked = Number(new URL(request.url).searchParams.get("limit"));
        return HttpResponse.json(all.slice(0, asked));
      }),
    );
    renderRoute("/branch/POS01");
    const more = await screen.findByRole("button", { name: "Xem thêm 20 đơn cũ hơn" });
    expect(asked).toBe(20);
    expect(screen.getAllByRole("button", { name: /^Hủy đơn/ })).toHaveLength(20);
    await userEvent.click(more);
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: /^Hủy đơn/ })).toHaveLength(30),
    );
    expect(asked).toBe(40);
    expect(screen.queryByRole("button", { name: /Xem thêm/ })).not.toBeInTheDocument();
  });

  describe("dish status on the order form (Flow C, section 7 of the specification)", () => {
    function withMenu(stale: boolean, dishes: Menu["dishes"]) {
      server.use(
        http.get("*/api/pos01/menu", () =>
          HttpResponse.json<Menu>({ stale, last_heard_at: "2026-11-20T09:15:00Z", dishes }),
        ),
      );
    }
    const DISHES: Menu["dishes"] = [
      { dish_id: "PHO_BO", name: "Phở bò", status: "CON" },
      { dish_id: "TRA_DA", name: "Trà đá", status: "HET" },
      { dish_id: "GOI_CUON", name: "Gỏi cuốn", status: "AN" },
    ];

    it("blocks a Sold-out dish and hides a Hidden one while the data is fresh", async () => {
      withMenu(false, DISHES);
      renderRoute("/branch/POS01");
      expect(await screen.findByRole("textbox", { name: "Phở bò" })).toBeEnabled();
      const tea = screen.getByRole("textbox", { name: "Trà đá" });
      expect(tea).toBeDisabled();
      expect(tea).toHaveAccessibleDescription("Hết");
      expect(screen.queryByRole("textbox", { name: "Gỏi cuốn" })).not.toBeInTheDocument();
      expect(screen.queryByText("Tình trạng món có thể đã thay đổi.")).not.toBeInTheDocument();
    });

    it("warns instead of blocking when the data is stale", async () => {
      withMenu(true, DISHES);
      renderRoute("/branch/POS01");
      const tea = await screen.findByRole("textbox", { name: "Trà đá" });
      expect(tea).toBeEnabled();
      expect(tea).toHaveAccessibleDescription("Có thể đã hết");
      expect(screen.getByText("Tình trạng món có thể đã thay đổi.")).toBeInTheDocument();
      expect(screen.getByRole("textbox", { name: "Phở bò" })).not.toHaveAccessibleDescription();
      expect(screen.queryByRole("textbox", { name: "Gỏi cuốn" })).not.toBeInTheDocument();
    });

    it("warns instead of blocking when the branch is offline, even with recent data", async () => {
      withMenu(false, DISHES);
      withMonitor({ connection: { connected: false, checked_at: "2026-11-20T09:15:00Z" } });
      renderRoute("/branch/POS01");
      expect(await screen.findByText("Tình trạng món có thể đã thay đổi.")).toBeInTheDocument();
      const tea = screen.getByRole("textbox", { name: "Trà đá" });
      expect(tea).toBeEnabled();
      expect(tea).toHaveAccessibleDescription("Có thể đã hết");
    });

    it("never sends a dish that became blocked or hidden after it was typed", async () => {
      let menu: Menu["dishes"] = [
        { dish_id: "PHO_BO", name: "Phở bò", status: "CON" },
        { dish_id: "TRA_DA", name: "Trà đá", status: "HET" },
        { dish_id: "GOI_CUON", name: "Gỏi cuốn", status: "CON" },
      ];
      let stale = true;
      let sent: unknown = null;
      server.use(
        http.get("*/api/pos01/menu", () =>
          HttpResponse.json<Menu>({ stale, last_heard_at: null, dishes: menu }),
        ),
        http.post("*/api/pos01/orders", async ({ request }) => {
          sent = await request.json();
          return HttpResponse.json(order(), { status: 201 });
        }),
      );
      renderRoute("/branch/POS01");
      // Stale data: the Sold-out tea can still be typed, and so can the rolls.
      await userEvent.type(await screen.findByRole("textbox", { name: "Trà đá" }), "2");
      await userEvent.type(screen.getByRole("textbox", { name: "Gỏi cuốn" }), "1");
      await userEvent.type(screen.getByRole("textbox", { name: "Phở bò" }), "1");
      // Fresh data arrives: the tea is blocked, the rolls are Hidden.
      stale = false;
      menu = [
        { dish_id: "PHO_BO", name: "Phở bò", status: "CON" },
        { dish_id: "TRA_DA", name: "Trà đá", status: "HET" },
        { dish_id: "GOI_CUON", name: "Gỏi cuốn", status: "AN" },
      ];
      act(() => {
        focusManager.setFocused(false);
        focusManager.setFocused(true);
      });
      await waitFor(() => expect(screen.getByRole("textbox", { name: "Trà đá" })).toBeDisabled());
      expect(screen.getByRole("textbox", { name: "Trà đá" })).toHaveValue("");
      expect(screen.queryByRole("textbox", { name: "Gỏi cuốn" })).not.toBeInTheDocument();
      await userEvent.click(screen.getByRole("button", { name: "Tạo đơn" }));
      await waitFor(() => expect(sent).toEqual({ items: [{ dish_id: "PHO_BO", quantity: 1 }] }));
    });

    it("lets a dish Inventory has said nothing about be ordered", async () => {
      withMenu(false, [{ dish_id: "PHO_BO", name: "Phở bò", status: null }]);
      renderRoute("/branch/POS01");
      expect(await screen.findByRole("textbox", { name: "Phở bò" })).toBeEnabled();
    });
  });
});
