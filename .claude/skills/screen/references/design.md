# Design of the screens

The decisions every screen follows, so that each screen does not invent its own. The direction: an operations tool, plain and dense, in the "minimalism and Swiss style for enterprise dashboards" family. Change this file, not a single screen, when a decision changes.

## Stack inside `frontend/`

- Mantine for every component (`AppShell`, `Table`, `Badge`, `Modal`, `Select`, `Notifications`, `Alert`). No second UI library, no Tailwind.
- Icons: `@tabler/icons-react`, the set Mantine's own examples use. SVG only, never emoji.
- TanStack Query for every API call. Queries poll every 2 seconds (`refetchInterval`) only while their screen is visible.
- The default Mantine font stack (system fonts). No web fonts: the demo must run without internet access.
- Light theme only. Kitchen and counter screens are used in bright rooms, and one theme halves the checking.

## Layout

- `AppShell` with a left navbar listing the six screens, each with an icon and a label; the current screen is highlighted. Below 768px the navbar collapses behind a burger button.
- The header shows the screen title and, on screens that belong to one branch, the branch selector and the connection indicator from `GET /monitor`.
- A banner at the top of the content when a service the screen needs does not answer: "Không kết nối được tới Bếp" and when it last answered. The rest of the screen keeps the last data it had, marked as possibly stale.
- Spacing follows Mantine's scale (`xs`…`xl`); no raw pixel margins in components.

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
