---
name: screen
description: Build or rework one screen of the web module, specification first. Runs only when the user calls /screen with a screen name (branch, kitchen, inventory, monitor, reports, demo).
argument-hint: <screen name>
disable-model-invocation: true
allowed-tools: Bash(.claude/skills/screen/scripts/screenshot.sh *)
---

# Build screen $ARGUMENTS

A screen shows what the services decide; it decides nothing itself. Everything below serves that principle (section 2 of `docs/03-implementation-plan.md`, "The screens decide nothing").

## Step 0: preconditions

1. Read `.claude/project-phase`. If it contains `docs`, stop and tell the user this skill is for the implementation phase. Do not change that file.
2. Find `$ARGUMENTS` in `references/screens.md`. If it is not there, list the screen names and stop.
3. Check that every API the screen needs exists in the generated types under `frontend/src/api/generated/`. If one is missing, stop and say which step of section 4 of document 03 must be finished first. Do not stub an API that does not exist yet.
4. If the screen's entry in `references/screens.md` lists an open question, ask the user before building that part. The answer goes into the relevant document, not only into the code.

## Step 1: list the states

1. Read the specification sections listed for the screen in `references/screens.md`, and the rows of section 6 of `docs/02-detailed-design.md` for its APIs, including every status code each API returns.
2. Write a state table in your reply before any code: each row is one thing the screen must show or one response it must handle (for example "order `DA_GIU` with flag `DANG_YEU_CAU`", "start returns 409"), with the section that requires it. Include the empty state, the loading state and "the service does not answer".
3. A row you cannot trace to a document section does not go in the table. If the screen seems to need it anyway, ask the user.

## Step 2: tests first

1. For each row of the state table, write a Vitest test in `frontend/src/screens/<screen>/` with Testing Library, and stub the API with MSW using the generated types. One row, one test; name the test after the row.
2. Run `docker compose exec frontend npx --no-install vitest run src/screens/<screen>` and confirm the new tests fail because the screen is missing, not because of a setup error.

## Step 3: build

1. Follow `references/design.md` for layout, components, status colours, labels and polling. Use the Tailwind CSS v4 + Radix UI primitives in `frontend/src/ui/`; do not add another UI library.
2. All Vietnamese labels for status codes and reasons come from the single label module named in `references/design.md`. Add missing labels there, using the glossary in `CLAUDE.md`.
3. Run the screen's tests until they pass, then `docker compose exec frontend npx --no-install tsc --noEmit` and `docker compose exec frontend npx --no-install biome check src`.

## Step 4: check and look

1. Go through `references/checklist.md` item by item. Fix what fails; for an item that does not apply, say why in one line.
2. With the Vite server running (the `frontend` container of `docker-compose.yml` serves it), take screenshots at the sizes the screen's entry names:
   `.claude/skills/screen/scripts/screenshot.sh <route> <width>x<height> <output.png>`
   Write them to the scratchpad or `/tmp`, never into the repository. Look at each screenshot and fix what is visibly wrong once; do not loop.

## Step 5: report

Give the user, in Vietnamese: the state table with the test that covers each row, the checklist items that failed and what you did, the screenshot paths, the files changed, and any open question. Do not commit unless the user asks.
