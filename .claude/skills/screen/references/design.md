# Design of the screens

The decisions every screen follows, so that each screen does not invent its own. The direction: a modern operations dashboard, the look of a standard admin console: white panels on a light grey page, one accent colour (indigo), quiet tables, figures at the top of office screens. The first version (plain and dense, titles straight on a white page, buttons of mixed sizes) was judged ugly and non-standard by @Naul on 22 Nov 2026 and reworked into this one. Change this file, not a single screen, when a decision changes. The values live in `frontend/src/theme.ts`; the page pieces in `frontend/src/components/layout.tsx`.

## Stack inside `frontend/`

- Mantine for every component (`AppShell`, `Table`, `Badge`, `Modal`, `Select`, `Notifications`, `Alert`). No second UI library, no Tailwind.
- Icons: `@tabler/icons-react`, the set Mantine's own examples use. SVG only, never emoji.
- TanStack Query for every API call. Queries poll every 2 seconds (`refetchInterval`) only while their screen is visible.
- The default Mantine font stack (system fonts). No web fonts: the demo must run without internet access.
- Light theme only. Kitchen and counter screens are used in bright rooms, and one theme halves the checking.

## Layout

- `AppShell` with a header carrying the product mark and name, and a left navbar listing the six screens in three groups (Vận hành: Chi nhánh, Bếp, Kho; Quản trị: Giám sát, Quản lý; Trình diễn: Demo), each with an icon and a label; the current screen is highlighted. Below 768px the navbar collapses behind a burger button.
- The page is light grey (`gray.0`); content sits on white surfaces with a hairline border, `md` radius and the faintest shadow (`Paper` and `Card` defaults in the theme).
- Every screen starts with `PageHeader`: the title (level 1, or level 2 inside the demo page), one dimmed line saying what the screen is for, and the screen's controls on the right (on a branch screen: the connection indicator from `GET /monitor`, the entries waiting to be sent, and the branch selector).
- Office screens (Kho, Giám sát, Quản lý) show a row of `Figures` under the header: three or four counts, each with a label, an icon and a colour that turns from grey to the warning colour when the count needs attention. Every figure is computed from an API response on screen; none is predicted.
- Lists and tables go in a `Panel`: a title bar (title, a grey count, actions on the right) over the content; a table runs to the panel's edges. An empty panel shows `Empty`: an icon and the sentence of "Empty states" below.
- The Kitchen is a board: each status column is a grey lane holding white ticket cards, the column's count in a filled badge next to its title. A ticket card has a coloured left edge for its status (indigo Chờ nấu, yellow Đang nấu).
- The branch order form is a grid of dish tiles: each tile has the dish name, its Flow C status line, and a stepper (minus, quantity, plus) around the quantity field; a picked tile turns indigo. Below the tiles, a summary line of what will be ordered, Xóa chọn and Tạo đơn.
- A banner at the top of the content when a service the screen needs does not answer: "Không kết nối được tới Bếp" and when it last answered. The rest of the screen keeps the last data it had, marked as possibly stale.
- Spacing follows Mantine's scale (`xs`…`xl`); no raw pixel margins in components.

## Type and buttons

- One page-title size (24px, weight 650), section titles at 15–18px. Never a heading larger than the page title, and no 34px default `h1`.
- Table headers are 12px, grey, on a `gray.0` band; numbers use tabular figures.
- Buttons: `sm` in office screens and tables, with a leading icon for the main actions. A row action that is not destructive is `default` (outlined grey); a destructive one is red `light` or `outline`; the one primary action of a panel is filled indigo. Kitchen buttons are 44px high and share the card's width.

## Status display

Every status is a `Badge` with a colour, an icon and the Vietnamese label. Colour is never the only signal.

| Code | Label | Colour | Meaning of the colour |
|---|---|---|---|
| `CHO_KHO` | Chờ Kho | gray | waiting |
| `DA_GIU` | Đã giữ | blue | in progress |
| `HUY_CHO_DON` | Hủy chờ đơn | orange | waiting, with a cancel recorded |
| `CHO_NAU` | Chờ nấu | blue | in progress |
| `DANG_NAU` | Đang nấu | yellow | in progress, can no longer be cancelled |
| `HOAN_TAT` | Hoàn tất | green | finished well |
| `DA_HUY` | Đã hủy | dark | finished, cancelled |
| `THAT_BAI` | Thất bại | red | finished badly |

The cancel flag is a second, outlined badge next to the status: `DANG_YEU_CAU` "Đang yêu cầu hủy" (orange, with the time waited), `BEP_KHONG_NAU` "Bếp sẽ không nấu" (teal). `KHONG` shows nothing. `cancel_message` is shown as a line of text under the order, not as a badge.

The Inventory record statuses and the reservation outcomes follow the same table where they appear; their labels are in the glossary of `CLAUDE.md`.

## Labels

- All Vietnamese text for status codes, flags, alert kinds and reason codes lives in one module, `frontend/src/labels.ts`. Components never spell a label themselves.
- Reasons come from section 10 of document 01. The customer-cancel reasons are still "proposed" there (section 11), so keep them in that one module where a change costs one line.
- Order ids are shown as their first 8 characters, with the full id in a tooltip and copyable.
- Times are shown as `HH:mm:ss` in the local time zone, durations as "3 phút", quantities with their unit and `font-variant-numeric: tabular-nums`.

## Behaviour

- **Polling without jumping.** A refetch updates rows in place: keep the row order stable (by creation time), reserve space for badges and messages, and do not show a spinner on a background refetch. Show a spinner only on the first load.
- **Buttons that send a request** are disabled with a loading state until the response arrives, so one press sends one request.
- **409** is a notice, not an error: a yellow notification "Phiếu vừa đổi trạng thái, đã tải lại", then refetch. Notifications close by themselves after 4 seconds and do not take focus.
- **4xx with a validation message** is shown next to the field it concerns. **5xx or no answer** is a red notification with a Retry action.
- **Confirmation** before Reject and before Cancel: a modal that also collects the reason, with the destructive button in red and separated from Close.
- **Empty states** say what will appear and why it is empty ("Chưa có phiếu nào đang chờ nấu").
- **Status changes** of a row are announced to screen readers through one polite live region per list, as a complete phrase ("Đơn a41f… đã chuyển sang Đã giữ").
- **Motion:** only Mantine's own transitions; respect `prefers-reduced-motion`.

## Sizes

- Counter and office screens: designed at 1280 wide, usable from 1024.
- Kitchen: tablet landscape (1024x768) and wall screen (1920x1080). Kitchen buttons are at least 44px high with 8px between them: staff press them quickly, sometimes with gloves.
- Online ordering: usable at 390 wide, one column.
