// The demo page: one test per row of its state table (.claude/skills/screen/SKILL.md, step 1).
// The states of the two panels themselves are the branch and Kitchen screens' tests.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderRoute } from "../../test/render";

describe("demo page", () => {
  it("puts the branch and the Kitchen side by side under one page heading", async () => {
    renderRoute("/demo/POS01");
    expect(await screen.findByRole("heading", { level: 1, name: "Demo" })).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { level: 2, name: "Chi nhánh POS01" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Bếp" })).toBeInTheDocument();
    expect(await screen.findByText(/Chưa có phiếu nào đang chờ nấu/)).toBeInTheDocument();
    expect(await screen.findByText(/Chưa có đơn nào/)).toBeInTheDocument();
  });

  it("keeps the branch selector on the demo page", async () => {
    renderRoute("/demo/POS01");
    await screen.findByRole("heading", { level: 2, name: "Chi nhánh POS01" });
    await userEvent.click(screen.getByRole("radio", { name: "ONLINE" }));
    expect(
      await screen.findByRole("heading", { level: 2, name: "Chi nhánh ONLINE" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Demo" })).toBeInTheDocument();
  });

  it("lists the demo scenarios of section 12 with how to run them", async () => {
    renderRoute("/demo/POS01");
    const guide = within(await screen.findByRole("region", { name: "Kịch bản demo" }));
    for (const n of ["1", "3", "4", "10", "36"]) {
      expect(guide.getByText(`Kịch bản ${n}`)).toBeInTheDocument();
    }
    expect(guide.getAllByText(/bin\/chaos offline pos01/).length).toBeGreaterThan(0);
  });

  it("says when the branch does not exist", async () => {
    renderRoute("/demo/POS99");
    expect(await screen.findByText("Không có chi nhánh POS99.")).toBeInTheDocument();
  });
});
