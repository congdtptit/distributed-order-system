---
paths:
  - "docs/**"
---

# Editing the document set

Applies when reading or editing files in `docs/`.

## Language

- Documents are written in English. Replies to the user are in Vietnamese.
- Use the terms in the glossary of `CLAUDE.md`. DB codes are unaccented Vietnamese in upper case, written in backticks, and are never translated.
- `docs/archive/` holds frozen Vietnamese originals. Do not edit them.

## Precedence

- 01 (specification) decides the business, 02 (design) follows 01, 03 (plan) follows both.
- To change the business, edit 01 first, then bring 02 and 03 in line in the same turn.

## Versions and change tables

- Editing the content of 01: raise the version in the title and on the first line, and add a row to the change table at the top of the file.
- Editing the content of 02 or 03: raise the revision number on the first line and add a "Changes in revision N" table with three columns: section, change, reason.
- Marking a point as confirmed (a `- [x]` box, with the date and who confirmed it) does not count as a revision. After marking it, update "Pending work" in `docs/README.md`.
- Never mark a point as confirmed on your own. Mark it only when the user says clearly that they agree.

## Numbers that must agree across files

- The scenario list in 01 section 12, in the step table of 02 section 7, and in the three tiers of 03 section 3.
- The specification version in the title of 01, on the first line of 02, in the introduction of 03 and in the README table.
- The revision number of 02 on its first line and in the README table.
- The number of event types stated at the start of 02 section 2 and the rows of the table below it.

After editing, run `python3 .claude/skills/doc-check/scripts/check_docs.py` from the project root. The `Stop` hook runs the same command and does not let a turn end while the documents disagree.

## Writing

- The SQL in sections 3, 4 and 5 of 02 has been trial-run; the results are in section 9 of 02. If you change SQL without running it again, say so in section 9.
- Do not copy the same content into two files. The later file points to the section of the earlier one.
