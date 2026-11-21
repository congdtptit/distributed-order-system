// Every Vietnamese label the screens show for a code, in one place
// (.claude/skills/screen/references/design.md, "Labels"). Components never spell a label
// themselves. The codes and their Vietnamese names follow the glossary in CLAUDE.md.

export type BadgeColor = "gray" | "blue" | "orange" | "yellow" | "green" | "dark" | "red" | "teal";

export interface StatusLabel {
  label: string;
  color: BadgeColor;
}

/** Branch order (table 3.1 of the specification). */
export const ORDER_STATUS = {
  CHO_KHO: { label: "Chờ Kho", color: "gray" },
  DA_GIU: { label: "Đã giữ", color: "blue" },
  HOAN_TAT: { label: "Hoàn tất", color: "green" },
  DA_HUY: { label: "Đã hủy", color: "dark" },
  THAT_BAI: { label: "Thất bại", color: "red" },
} as const satisfies Record<string, StatusLabel>;

/** Kitchen record (table 3.2). CHUA_CO is only a lock row and is never shown. */
export const KITCHEN_STATUS = {
  HUY_CHO_DON: { label: "Hủy chờ đơn", color: "orange" },
  CHO_NAU: { label: "Chờ nấu", color: "blue" },
  DANG_NAU: { label: "Đang nấu", color: "yellow" },
  HOAN_TAT: { label: "Hoàn tất", color: "green" },
  DA_HUY: { label: "Đã hủy", color: "dark" },
  THAT_BAI: { label: "Thất bại", color: "red" },
} as const satisfies Record<string, StatusLabel>;

/** Inventory record (table 3.3). */
export const INVENTORY_STATUS = {
  DANG_GIU: { label: "Đang giữ", color: "blue" },
  THAT_BAI: { label: "Thất bại", color: "red" },
  DA_TRA: { label: "Đã trả", color: "dark" },
  DA_DUNG: { label: "Đã dùng", color: "green" },
} as const satisfies Record<string, StatusLabel>;

/** The "Cancel requested" flag at the branch. KHONG shows nothing. */
export const CANCEL_FLAG = {
  DANG_YEU_CAU: { label: "Đang yêu cầu hủy", color: "orange" },
  BEP_KHONG_NAU: { label: "Bếp sẽ không nấu", color: "teal" },
} as const satisfies Record<string, StatusLabel>;

/** Flow D alert kinds. */
export const ALERT_KIND = {
  CAN_KIEM_TRA: "Cần kiểm tra",
  LENH_KHONG_KHOP: "Lệnh không khớp",
  HUY_SAI_CHI_NHANH: "Hủy sai chi nhánh",
} as const satisfies Record<string, string>;

// Reason codes (section 10 of the specification) are added here when the services define
// them in step 1; the customer-cancel reasons are still "proposed" there.
