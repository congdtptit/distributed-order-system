// The Monitor screen: one test per row of the state table (.claude/skills/screen/SKILL.md,
// step 1). Every service is stubbed by MSW with the generated API types.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, HttpResponse, http } from "msw";
import { renderRoute } from "../../test/render";
import { EMPTY_MONITOR, QUIET_CONSUMER, server } from "../../test/server";

const ID = "a41f0c2e-1111-4222-8333-444455556666";

function rowOf(service: string) {
  const row = screen.getByRole("row", { name: new RegExp(`^${service}\\b`) });
  return within(row);
}

describe("monitor screen", () => {
  it("shows a loader on the first load", async () => {
    server.use(
      http.get("*/api/kitchen/monitor", async () => {
        await delay("infinite");
        return HttpResponse.json(QUIET_CONSUMER("kitchen"));
      }),
    );
    renderRoute("/monitor");
    expect(await screen.findAllByLabelText("Đang tải")).not.toHaveLength(0);
  });

  it("has one row per service with its state", async () => {
    server.use(
      http.get("*/api/pos01/monitor", () =>
        HttpResponse.json({
          ...EMPTY_MONITOR,
          connection: { connected: false, checked_at: "2026-11-20T09:15:00Z" },
          waiting_to_send: 4,
          awaiting_inventory: [
            {
              order_id: ID,
              created_at: "2026-11-20T09:00:00Z",
              waited_s: 900,
              cancel_flag: "KHONG",
            },
          ],
        }),
      ),
    );
    renderRoute("/monitor");
    await screen.findByText("4 mục chờ gửi");
    for (const service of ["POS01", "POS02", "ONLINE", "Kho", "Bếp"]) {
      expect(rowOf(service).getByText("Đang trả lời")).toBeInTheDocument();
    }
    const pos01 = rowOf("POS01");
    expect(pos01.getByText("Mất kết nối Kafka")).toBeInTheDocument();
    expect(pos01.getByText("1 đơn chờ Kho quá lâu")).toBeInTheDocument();
  });

  it("shows a service that does not answer as down and keeps the others", async () => {
    server.use(http.get("*/api/pos02/monitor", () => HttpResponse.error()));
    renderRoute("/monitor");
    await screen.findAllByText("Đang trả lời");
    expect(await screen.findByText("Không trả lời")).toBeInTheDocument();
    expect(rowOf("POS02").getByText("Không trả lời")).toBeInTheDocument();
    expect(rowOf("Bếp").getByText("Đang trả lời")).toBeInTheDocument();
  });

  it("warns of a slow consumer per topic", async () => {
    server.use(
      http.get("*/api/kitchen/monitor", () =>
        HttpResponse.json({
          ...QUIET_CONSUMER("kitchen"),
          topics: [
            {
              topic: "kitchen-orders",
              unread: 12,
              oldest_unread_at: "2026-11-20T09:00:00Z",
              oldest_unread_age_s: 420,
              slow: true,
            },
            {
              topic: "menu-events",
              unread: 0,
              oldest_unread_at: null,
              oldest_unread_age_s: null,
              slow: false,
            },
          ],
        }),
      ),
    );
    renderRoute("/monitor");
    const region = within(await screen.findByRole("region", { name: "Consumer chậm" }));
    expect(await region.findByText("kitchen-orders")).toBeInTheDocument();
    expect(region.getByText(/12 tin chưa đọc, cũ nhất 7 phút/)).toBeInTheDocument();
    expect(region.queryByText("menu-events")).not.toBeInTheDocument();
  });

  it("lists the alerts of every service and filters them by kind", async () => {
    server.use(
      http.get("*/api/kitchen/alerts", () =>
        HttpResponse.json([
          {
            id: 1,
            kind: "HUY_SAI_CHI_NHANH",
            order_id: ID,
            event_id: null,
            source_topic: "cancel-events.POS02",
            source_partition: 0,
            source_offset: 1,
            detail: { origin_branch: "POS01", dismissed: ["POS02"] },
            created_at: "2026-11-20T09:20:00Z",
          },
        ]),
      ),
      http.get("*/api/inventory/alerts", () =>
        HttpResponse.json([
          {
            id: 7,
            kind: "LENH_KHONG_KHOP",
            order_id: ID,
            event_id: null,
            source_topic: "stock-commands",
            source_partition: 0,
            source_offset: 2,
            detail: { event_type: "ReleaseRequested", record_status: null },
            created_at: "2026-11-20T09:10:00Z",
          },
        ]),
      ),
      http.get("*/api/online/monitor", () =>
        HttpResponse.json({
          ...EMPTY_MONITOR,
          message_alerts: {
            count: 1,
            latest: [
              {
                kind: "CAN_KIEM_TRA",
                order_id: null,
                event_id: null,
                source_topic: "status-events.ONLINE",
                detail: { error: "unknown event_type" },
                created_at: "2026-11-20T09:05:00Z",
              },
            ],
          },
        }),
      ),
    );
    renderRoute("/monitor");
    const region = within(await screen.findByRole("region", { name: "Cảnh báo" }));
    expect(await region.findByText(/Bếp · Hủy sai chi nhánh/)).toBeInTheDocument();
    expect(await region.findByText(/Kho · Lệnh không khớp/)).toBeInTheDocument();
    expect(await region.findByText(/ONLINE · Cần kiểm tra/)).toBeInTheDocument();
    await userEvent.click(region.getByRole("radio", { name: "Lệnh không khớp" }));
    expect(region.getByText(/Kho · Lệnh không khớp/)).toBeInTheDocument();
    expect(
      region.queryByText(/Hủy sai chi nhánh ·|Bếp · Hủy sai chi nhánh/),
    ).not.toBeInTheDocument();
    expect(region.queryByText(/ONLINE · Cần kiểm tra/)).not.toBeInTheDocument();
  });

  it("explains an empty alert list and offers no action on orders", async () => {
    renderRoute("/monitor");
    expect(await screen.findByText(/Không có cảnh báo nào/)).toBeInTheDocument();
    const main = screen.getByRole("main");
    expect(within(main).queryAllByRole("button")).toHaveLength(0);
  });
});
