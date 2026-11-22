import { screen } from "@testing-library/react";
import { CANCEL_FLAG, INVENTORY_STATUS, KITCHEN_STATUS, ORDER_STATUS } from "./labels";
import { SCREENS } from "./screens";
import { renderRoute as renderAt } from "./test/render";

describe("layout", () => {
  it("lists the six screens in the navbar", () => {
    renderAt("/kitchen");
    const nav = screen.getByRole("navigation", { name: "Các màn hình" });
    for (const s of SCREENS) {
      expect(nav).toHaveTextContent(s.label);
    }
  });

  it("highlights the current screen and shows its title", () => {
    renderAt("/kitchen");
    expect(screen.getByRole("heading", { level: 1, name: "Bếp" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Bếp" })).toHaveAttribute("data-active", "true");
  });

  it("opens the branch screen of POS01 at the root", async () => {
    renderAt("/");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Chi nhánh POS01" }),
    ).toBeInTheDocument();
  });
});

describe("labels", () => {
  it("names every status of tables 3.1, 3.2 and 3.3 and both cancel flags", () => {
    expect(Object.keys(ORDER_STATUS)).toEqual([
      "CHO_KHO",
      "DA_GIU",
      "HOAN_TAT",
      "DA_HUY",
      "THAT_BAI",
    ]);
    expect(Object.keys(KITCHEN_STATUS)).toEqual([
      "HUY_CHO_DON",
      "CHO_NAU",
      "DANG_NAU",
      "HOAN_TAT",
      "DA_HUY",
      "THAT_BAI",
    ]);
    expect(Object.keys(INVENTORY_STATUS)).toEqual(["DANG_GIU", "THAT_BAI", "DA_TRA", "DA_DUNG"]);
    expect(Object.keys(CANCEL_FLAG)).toEqual(["DANG_YEU_CAU", "BEP_KHONG_NAU"]);
  });
});
