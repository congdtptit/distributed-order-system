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

/** The stock-check flag of an ingredient (BR6). */
export const STOCK_CHECK = {
  CHO_KIEM_KHO: { label: "Chờ kiểm kho", color: "red" },
} as const satisfies Record<string, StatusLabel>;

/** Flow D alert kinds. */
export const ALERT_KIND = {
  CAN_KIEM_TRA: "Cần kiểm tra",
  LENH_KHONG_KHOP: "Lệnh không khớp",
  HUY_SAI_CHI_NHANH: "Hủy sai chi nhánh",
} as const satisfies Record<string, string>;

/** Reason codes of section 10 of the specification (backend/common/src/common/reasons.py). */
export const REASON = {
  INSUFFICIENT_INGREDIENTS: "Không đủ nguyên liệu",
  AWAITING_STOCK_CHECK: "Nguyên liệu đang chờ kiểm kho",
  NO_RECIPE: "Món không có công thức",
  ORDER_EXPIRED: "Đơn quá hạn",
  FUTURE_CREATION_TIME: "Giờ tạo đơn không hợp lệ (ở tương lai)",
  INVALID_ORDER_DATA: "Dữ liệu đơn không hợp lệ",
  EQUIPMENT_FAILURE: "Hỏng thiết bị",
  SHORT_STAFFED: "Thiếu nhân viên",
  SPOILED_INGREDIENT: "Nguyên liệu hỏng",
  CHANGED_MIND: "Khách đổi ý",
  WAITED_TOO_LONG: "Khách chờ quá lâu",
  WRONG_ORDER_ENTERED: "Thu ngân nhập sai đơn",
} as const satisfies Record<string, string>;

/** The reasons a cashier or customer may give for a cancel ("proposed" in section 11 of the
 * specification, so they live here where a change costs one line). */
export const CUSTOMER_CANCEL_REASONS = [
  "CHANGED_MIND",
  "WAITED_TOO_LONG",
  "WRONG_ORDER_ENTERED",
] as const;

export function reasonLabel(code: string | null): string | null {
  if (code === null) return null;
  return (REASON as Record<string, string>)[code] ?? code;
}

/** Send state of an order's create-order entry: the texts of BR5. */
export const SEND_STATE = {
  CHUA_GUI: "Chưa gửi, bếp chưa nhận",
  DANG_GUI: "Đang gửi, chưa biết bếp đã nhận chưa",
  DA_GUI: "Đã gửi đi",
} as const satisfies Record<string, string>;

/** Send state of the latest cancel entry (BR5: a request not yet sent is no guarantee). */
export const CANCEL_SEND_STATE = {
  CHUA_GUI: "Chưa gửi yêu cầu hủy, chưa chắc hủy được",
  DANG_GUI: "Đang gửi yêu cầu hủy, chưa chắc hủy được",
  DA_GUI: "Đã gửi yêu cầu hủy, chờ Bếp trả lời",
} as const satisfies Record<string, string>;

/** ``cancel_message`` holds a fixed English text (section 5 of document 02). */
export const CANCEL_MESSAGE: Record<string, string> = {
  "Cannot cancel: the kitchen has started cooking": "Không hủy được: bếp đã bắt đầu nấu",
};

/** The reasons Kitchen staff may give for a rejection (section 10 of the specification). */
export const KITCHEN_REJECTION_REASONS = [
  "EQUIPMENT_FAILURE",
  "SHORT_STAFFED",
  "SPOILED_INGREDIENT",
] as const;

/** What the cancel dialog says before the request: the branch, not the screen, decides
 * which case applies (BR9, section 6 of the specification). */
export const CANCEL_EXPLANATION =
  "Đơn chưa từng được gửi đi thì chi nhánh hủy ngay, chắc chắn không được nấu. Đơn đã gửi đi thì Bếp quyết định: nếu bếp đã bắt đầu nấu thì không hủy được.";
