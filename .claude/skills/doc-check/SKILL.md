---
name: doc-check
description: Check that the documents in docs/ agree with each other (misaligned tables, broken links, the scenario list across the specification, the design and the plan, version numbers). Use after editing any file in docs/, or when the user asks whether the documents are consistent.
allowed-tools: Bash(python3 *)
---

# Check the document set

Run the script; do not compare the files by eye:

```
python3 "${CLAUDE_SKILL_DIR}/scripts/check_docs.py"
```

The script exits 0 and prints a one-line summary when the documents agree. On a mismatch it exits 1 and prints each problem with the file name.

## Handling the result

- Misaligned table, unclosed code block, broken link: fix it in the file named.
- Scenario list mismatch: section 12 of document 01 is the master list. Fix the step table in section 7 of document 02 and the three tiers in section 3 of document 03 to match it, never the other way round.
- Version mismatch: the title of document 01 and the first line of document 02 are the masters. Fix the places that repeat them.
- A mismatch that needs the user's decision (for example a new scenario whose step is unclear): say so in your reply; do not choose for them.

After fixing, run the script again until it passes. Give the user the final summary line, in Vietnamese.

## What the script checks

- Every `.md` file directly in `docs/`: tables are aligned, code blocks are closed, links to other `.md` files exist.
- Document 01: BR1–BR12 are all present; scenario numbers in section 12 are unique and match the count stated at the start of the section.
- Document 02: the number of event types matches the count stated at the start of section 2; the step table in section 7 covers exactly the scenario list; the points in section 8 are numbered consecutively; the specification version on the first line matches document 01.
- Document 03: the three tiers in section 3 partition the scenario list with no overlap and no gap.
- README, `CLAUDE.md` and the files under `.claude/`: versions and document paths are still right.

The script does not check the business content. Use the `doc-auditor` subagent for that.
