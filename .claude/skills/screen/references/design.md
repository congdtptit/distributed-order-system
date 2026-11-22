# Design of the screens

The decisions every screen follows, so that each screen shares one calm visual language without forcing every workflow into the same box template. After an earlier Mantine restyle (22 Nov 2026) still felt like a rigid admin template, the frontend was rebuilt from scratch on **Tailwind CSS v4**, **Radix UI** primitives, **Lucide** icons, and offline-bundled **Be Vietnam Pro** + **JetBrains Mono** fonts. Change this file, not a single screen, when a shared visual decision changes. The semantic tokens live in `frontend/src/styles/tokens.css` and `app.css`; reusable primitives in `frontend/src/ui/`; the shell in `frontend/src/components/AppShell.tsx`.

## Stack inside `frontend/`

- **Tailwind CSS v4** (`@tailwindcss/vite`) for layout, spacing, and surface hierarchy.
- **Radix UI** (`@radix-ui/react-dialog`, `@radix-ui/react-select`, `@radix-ui/react-tooltip`, `@radix-ui/react-checkbox`) for accessible overlays, comboboxes, tooltips, and checkboxes, wrapped in `frontend/src/ui/`.
- **Icons:** `lucide-react` (SVG only, never emoji).
- **Typography (100% offline):** `@fontsource/be-vietnam-pro` (400–700) for Vietnamese UI text and `@fontsource/jetbrains-mono` (400–600) for order IDs, timestamps, quantities, and CLI snippets. No CDN fonts or external scripts.
- **TanStack Query** for every API call. Queries poll every 2 seconds (`refetchInterval`) only while their screen is visible.
- **Multi-layer Hybrid Light theme:** dark slate-navy navigation anchor paired with a cool-slate workspace canvas and crisp white cards, giving clear depth for live operations and high print legibility for the course report.

## Visual direction and layout

- **Palette:** Deep Slate-Navy sidebar & POS order slip (`#0F172A`), cool-slate canvas (`#EAEFF5`), crisp `#FFFFFF` floating cards/tables with soft elevation, and Royal Cobalt (`#2563EB`) for active navigation and POS submit CTAs — reserving sky, amber, orange, emerald, charcoal, and rose for semantic status signals.
- **Shell (`AppShell`):** Collapsible left sidebar rail (`224px` ↔ `64px`) grouping the six screens under *Vận hành*, *Quản trị*, and *Trình diễn*, paired with a compact sticky translucent topbar showing the breadcrumb and `Làm mới 2s` live indicator. Below `768px` the sidebar slides over via a menu button. All shell controls live outside `<main>` so read-only screens (`/monitor`, `/reports`) keep zero `<button>` elements inside `<main>`.
- **Purpose-built screen layouts (no boilerplate KPI grids or prose walls under `h1`):**
  - **Chi nhánh:** Header with `POS01 | POS02 | ONLINE` segmented radio, Kafka connection badge, and waiting-to-send count; Flow D alerts when active; a POS split-pane (`8/12` interactive dish cards with stepper + `4/12` sticky *Phiếu đặt món* order slip); and the live orders table below.
  - **Bếp (KDS):** Two lanes (*Chờ nấu* `8/12`, *Đang nấu* `4/12`). Ticket cards use equal-height stretch (`h-full flex-col justify-between`) with clean uniform 1px semantic borders, bold dishes/quantities first, reserved ingredients, red stock-check warning when present, and pinned `min-h-[44px]` action buttons. Column names are not repeated as redundant badges on each card.
  - **Kho:** Compact top summary badges + red banner when ingredients await stock check; stock ledger table with mini stacked capacity bars (*Có thể giữ / Đang giữ / Hao hụt*) under each ingredient name; flagged items sorted first.
  - **Giám sát:** Compact cluster status badges, live-dot service health table, slow-consumer panel, and kind-filterable alerts feed using native radio pills (`SegmentedRadio`).
  - **Quản lý:** Chain-wide stacked proportion bar across all five order statuses, branch status table with replication freshness dots next to `dữ liệu tính đến`, horizontal reason-ratio bars per branch, and the methodology note strip below.
  - **Demo:** Compact one-row scenario pill bar (`Kịch bản 1, 3, 4, 10, 36`) expanding inline steps + expected outcome on click, optional *Xem Kho* toggle, and `Chi nhánh` | `Bếp` side by side.
- **Unreachable service:** Red `ServiceBanner` at the top of the screen keeping the last known data visible.

## Status display

Every status badge carries a semantic tone, an icon, and the Vietnamese label (`frontend/src/components/common.tsx` + `frontend/src/labels.ts`). Colour is never the only signal.

| Code | Label | Tone | Meaning |
|---|---|---|---|
| `CHO_KHO` | Chờ Kho | gray | waiting |
| `DA_GIU` | Đã giữ | blue | in progress |
| `HUY_CHO_DON` | Hủy chờ đơn | orange | waiting, cancel recorded |
| `CHO_NAU` | Chờ nấu | blue | in progress |
| `DANG_NAU` | Đang nấu | yellow | in progress, can no longer be cancelled |
| `HOAN_TAT` | Hoàn tất | green | finished well |
| `DA_HUY` | Đã hủy | dark | finished, cancelled |
| `THAT_BAI` | Thất bại | red | finished badly |

The cancel flag is a second outlined badge next to the status: `DANG_YEU_CAU` "Đang yêu cầu hủy" (orange, with time waited), `BEP_KHONG_NAU` "Bếp sẽ không nấu" (teal). `KHONG` shows nothing. `cancel_message` appears as a line of text below the badge.

## Labels & Behaviour

- All Vietnamese labels for status codes, flags, alert kinds, and reason codes live in `frontend/src/labels.ts`.
- Order ids show their first 8 characters in `JetBrains Mono`, with the full id in a tooltip and copyable.
- Times use `HH:mm:ss`, durations use `"3 phút"`, quantities use Vietnamese formatting and `tabular-nums`.
- **Polling without jumping:** Refetches update rows in place; loaders appear only on the initial fetch.
- **409** shows a yellow 4-second toast (`"Phiếu vừa đổi trạng thái, đã tải lại"` / `"Đơn vừa đổi trạng thái, đã tải lại"`) and refetches.
- **400 / 422** validation messages appear next to their field; **5xx / network failure** shows a red toast with retry where applicable.
- **Confirmation:** Cancel and Reject use accessible Radix dialogs requiring a reason, with the destructive button in rose red separated from Close.
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` disables transitions and animations.

## Sizes

- Counter and office screens: designed at `1280`–`1440` wide, usable from `1024`.
- Kitchen: tablet landscape (`1024×768`) and wall screen (`1920×1080`), action buttons at least `44px` tall with `8px` spacing.
- Online ordering: single column at `390` wide with table scrolling cleanly inside its container.
