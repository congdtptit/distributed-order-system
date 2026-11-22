// The Management screen: one test per row of the state table (.claude/skills/screen/SKILL.md,
// step 1). The Order Query Service is stubbed by MSW with the generated API types.

import { screen, within } from "@testing-library/react";
import { delay, HttpResponse, http } from "msw";
import type { BranchSummary, Summary } from "../../api/reports";
import { clock } from "../../components/common";
import { renderRoute } from "../../test/render";
import { server } from "../../test/server";

const ZERO = { CHO_KHO: 0, DA_GIU: 0, HOAN_TAT: 0, DA_HUY: 0, THAT_BAI: 0 };

function line(branch_id: string, rest: Partial<BranchSummary> = {}): BranchSummary {
  return {
    branch_id,
    data_as_of: "2026-11-20T09:14:58Z",
    data_age_s: 2,
    total: 0,
    by_status: ZERO,
    reasons: [],
    ...rest,
  };
}

function answer(branches: BranchSummary[]) {
  server.use(
    http.get("*/api/reports/reports/summary", () =>
      HttpResponse.json<Summary>({ generated_at: "2026-11-20T09:15:00Z", branches }),
    ),
  );
}

function rowOf(name: string) {
  return within(screen.getByRole("row", { name: new RegExp(`^${name}\\b`) }));
}

describe("management screen", () => {
  it("shows a loader on the first load", async () => {
    server.use(
      http.get("*/api/reports/reports/summary", async () => {
        await delay("infinite");
        return HttpResponse.json({});
      }),
    );
    renderRoute("/reports");
    expect(await screen.findByLabelText("Đang tải")).toBeInTheDocument();
  });

  it("says when the report service does not answer", async () => {
    server.use(http.get("*/api/reports/reports/summary", () => HttpResponse.error()));
    renderRoute("/reports");
    expect(await screen.findByText("Không kết nối được tới Báo cáo")).toBeInTheDocument();
  });

  it("gives each branch its own data-as-of time and how old it is", async () => {
    answer([
      line("POS01", { data_as_of: "2026-11-20T09:12:00Z", data_age_s: 180 }),
      line("POS02", { data_as_of: "2026-11-20T09:14:58Z", data_age_s: 2 }),
    ]);
    renderRoute("/reports");
    await screen.findByRole("row", { name: /^POS01/ });
    expect(
      rowOf("POS01").getByText(`${clock("2026-11-20T09:12:00Z")} (cách đây 3 phút)`),
    ).toBeInTheDocument();
    expect(
      rowOf("POS02").getByText(`${clock("2026-11-20T09:14:58Z")} (cách đây 2 giây)`),
    ).toBeInTheDocument();
  });

  it("says when a branch's data has not reached the report yet", async () => {
    answer([line("ONLINE", { data_as_of: null, data_age_s: null })]);
    renderRoute("/reports");
    await screen.findByRole("row", { name: /^ONLINE/ });
    expect(rowOf("ONLINE").getByText("Chưa có dữ liệu")).toBeInTheDocument();
  });

  it("counts orders by status per branch and for the whole chain", async () => {
    answer([
      line("POS01", {
        total: 7,
        by_status: { CHO_KHO: 1, DA_GIU: 2, HOAN_TAT: 3, DA_HUY: 1, THAT_BAI: 0 },
      }),
      line("POS02", {
        total: 2,
        by_status: { CHO_KHO: 0, DA_GIU: 0, HOAN_TAT: 1, DA_HUY: 0, THAT_BAI: 1 },
      }),
    ]);
    renderRoute("/reports");
    const table = within(await screen.findByRole("table", { name: "Đơn theo trạng thái" }));
    const headers = table.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual([
      "Chi nhánh",
      "Dữ liệu tính đến",
      "Chờ Kho",
      "Đã giữ",
      "Hoàn tất",
      "Đã hủy",
      "Thất bại",
      "Tổng",
    ]);
    // The branch name is the row header; the cells are the data-as-of time, then the counts.
    const cells = (name: string) =>
      rowOf(name)
        .getAllByRole("cell")
        .slice(1)
        .map((c) => c.textContent);
    expect(cells("POS01")).toEqual(["1", "2", "3", "1", "0", "7"]);
    expect(cells("POS02")).toEqual(["0", "0", "1", "0", "1", "2"]);
    expect(cells("Toàn chuỗi")).toEqual(["1", "2", "4", "1", "1", "9"]);
  });

  it("counts cancelled and failed orders by reason per branch", async () => {
    answer([
      line("POS01", {
        reasons: [
          { status: "DA_HUY", reason_code: "CHANGED_MIND", count: 2 },
          { status: "DA_HUY", reason_code: "EQUIPMENT_FAILURE", count: 1 },
          { status: "THAT_BAI", reason_code: "INSUFFICIENT_INGREDIENTS", count: 4 },
        ],
      }),
      line("POS02"),
    ]);
    renderRoute("/reports");
    const pos01 = within(await screen.findByRole("region", { name: "Lý do ở POS01" }));
    expect(pos01.getByText("Khách đổi ý")).toBeInTheDocument();
    expect(pos01.getByText("Hỏng thiết bị")).toBeInTheDocument();
    expect(pos01.getByText("Không đủ nguyên liệu")).toBeInTheDocument();
    expect(pos01.getByRole("row", { name: /Khách đổi ý/ })).toHaveTextContent("2");
    expect(pos01.getByRole("row", { name: /Không đủ nguyên liệu/ })).toHaveTextContent("4");
    const pos02 = within(screen.getByRole("region", { name: "Lý do ở POS02" }));
    expect(pos02.getByText("Chưa có đơn nào bị hủy hay thất bại.")).toBeInTheDocument();
  });

  it("says that a cancel request still pending at the Kitchen is not counted", async () => {
    answer([line("POS01")]);
    renderRoute("/reports");
    expect(
      await screen.findByText(/yêu cầu hủy đang chờ ở Bếp không được tính/i),
    ).toBeInTheDocument();
  });

  it("offers no action that changes data", async () => {
    answer([line("POS01")]);
    renderRoute("/reports");
    await screen.findByRole("row", { name: /^POS01/ });
    expect(within(screen.getByRole("main")).queryAllByRole("button")).toHaveLength(0);
  });
});
