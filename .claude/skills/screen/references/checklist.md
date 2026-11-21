# Checklist before handing over a screen

Go through every item. The ids in backticks name the general UI rule behind an item (they come from a UI/UX rule set that was filtered for this project: web screens on desktop and tablet, Mantine, no marketing pages, no native mobile app).

## The project's own rules

- [ ] Every status, flag and message on screen comes from an API response. Nothing is inferred, predicted or kept after the service reports a different value.
- [ ] Every state in the state table of step 1 has a passing test.
- [ ] Every 409 the screen's APIs can return reloads the item and shows the notice from `design.md`.
- [ ] A service that does not answer shows the banner, and the rest of the screen still works.
- [ ] Labels come from `frontend/src/labels.ts`; no status code is shown raw.
- [ ] The only API types used are the generated ones; no hand-written request or response type.
- [ ] No asset is loaded from the internet (fonts, icons, scripts).

## Accessibility

- [ ] Text contrast at least 4.5:1, badge text included (`color-contrast`, `contrast-feedback`).
- [ ] Every control is reachable with Tab in visual order and shows a visible focus ring (`keyboard-nav`, `focus-states`).
- [ ] Icon-only buttons have an accessible name; icons next to text are hidden from screen readers (`aria-labels`, `icon-context`).
- [ ] Colour is never the only signal: badges carry an icon and a label, the red ticket warning carries text (`color-not-only`, `color-not-decorative-only`).
- [ ] Every form field has a visible label, and its error sits under it (`input-labels`, `error-placement`).
- [ ] Modals close with Escape and a visible Close button, and return focus to the button that opened them (`escape-routes`, `modal-escape`).
- [ ] The notifications and the sticky header never hide the focused control (`focus-not-obscured`).
- [ ] Status changes are announced through one polite live region, without moving focus (`contextual-live-badge-updates`, `toast-accessibility`).
- [ ] Reduced motion is respected (`reduced-motion`).

## Interaction and feedback

- [ ] A button that sends a request is disabled with a loading state until the answer arrives (`loading-buttons`).
- [ ] Reject and Cancel ask for confirmation, and the destructive button is red and set apart (`confirmation-dialogs`, `destructive-emphasis`).
- [ ] An error says what went wrong and what to do next; a failed request offers Retry (`error-clarity`, `error-recovery`, `timeout-feedback`).
- [ ] Notifications close by themselves after about 4 seconds (`toast-dismiss`).
- [ ] Empty lists explain why they are empty (`empty-states`).
- [ ] Disabled controls look disabled and are not focusable as active controls (`disabled-states`).
- [ ] Kitchen buttons are at least 44px high with 8px gaps; other pointer targets at least 24x24px (`touch-target-size`, `touch-spacing`, `web-target-size`).

## Layout and data

- [ ] A background refetch does not move rows or push buttons around (`content-jumping`).
- [ ] Numbers, quantities and times use tabular figures (`number-tabular`).
- [ ] Long ids wrap or truncate with the full value available in a tooltip (`truncation-strategy`, `long-token-wrapping`).
- [ ] No horizontal scroll of the page at the screenshot sizes of the screen; wide tables scroll inside their own container (`horizontal-scroll`).
- [ ] The current screen is highlighted in the navbar, and the screen has its own URL that survives a reload (`nav-state-active`, `deep-linking`).
- [ ] Headings go in order without skipping a level (`heading-hierarchy`).
