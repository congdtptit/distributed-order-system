---
paths:
  - "frontend/**"
---

# Screens (TypeScript)

The `frontend` module is a client of the services' APIs. Its place in the system is set by section 2 of `docs/03-implementation-plan.md` (the principle "The screens decide nothing") and by the note on screens in section 6 of `docs/02-detailed-design.md`.

## Read before editing

- `docs/02-detailed-design.md` section 6: the APIs, their status codes, and the notes below the table.
- The entry of the screen being changed in `.claude/skills/screen/references/screens.md`: the specification sections, the APIs and the states it must handle.
- `.claude/skills/screen/references/design.md`: layout, status badges, labels and behaviour shared by every screen.

A new screen, or a rework of one, goes through the `/screen <name>` skill.

## Design guidance from ui-ux-pro-max

The `ui-ux-pro-max` skill is a general UI/UX database. For this project, `design.md` above and the rules below win over anything it suggests. Use only its targeted searches (`--domain ux`, `--stack react`) for a specific concern. Do not run its `--design-system` or `--persist` modes: they propose landing-page patterns and web fonts that do not fit an operations tool that must run offline.

## Rules

- Call only the APIs in section 6 of document 02, through the types generated in `src/api/generated/`. Do not edit the generated files; regenerate them from the services' OpenAPI documents.
- Show the status the service returns. Never infer or predict a status on screen, and never hide a status because a newer one is "expected".
- A 409 is the normal result of a race (BR7). Reload the item and show a short notice; do not show it as an error.
- `POST /orders` returns before Inventory decides. The order appears as Awaiting Inventory, and the screen polls until it changes.
- The Cancel button is hidden when the order is in a terminal status. While the flag is `DANG_YEU_CAU` the screen shows that the request is pending, and does not offer a second cancel.
- Blocking a Sold-out dish while the data is fresh, and the "may be sold out" warning when it is stale, are the only rules enforced on screen alone (point 5 in section 8 of document 02). They belong to phase 2.
- Labels are in Vietnamese, using the glossary in `CLAUDE.md`. Status codes such as `CHO_KHO` are mapped to their Vietnamese names in one place, not in each component.
- When a service does not answer, show which service is down and keep the rest of the screen working.
- No assets from a CDN: the demo must run without internet access.

## Tests

Each display rule of the specification that a screen implements has a Vitest test, with the API responses stubbed by MSW. These tests carry no `kb` marker; the scenarios are proven at the service level.
