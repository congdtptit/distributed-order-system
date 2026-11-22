---
paths:
  - "report/**"
---

# Writing and formatting the course report

Applies when creating, editing, or rebuilding files in `report/`.

## Language and style

- Read and follow `.claude/skills/vietnamese-tech-report-writing/SKILL.md` (along with its `references/anti-ai-patterns-vi.md` and `references/before-after-examples.md`) for Vietnamese technical prose, objective tone, and elimination of AI writing tells.
- Keep all system/code identifiers in English as required by `CLAUDE.md` (service names, database/table/column names, Kafka topics, event names, API paths, and upper-case status/reason codes in backticks such as `DANG_GIU`, `CHO_NAU`, `INSUFFICIENT_INGREDIENTS`).
- Place table captions **above** every table (`*Bảng X.Y. ...*`) and figure/diagram captions **below** every figure (`*Hình X.Y. ...*`), and reference every table and figure directly in the surrounding prose.

## Word export (`report/build.sh`)

- `report/build.sh` uses `report/reference.docx` as the Pandoc `--reference-doc` (A4, `Times New Roman`, PTIT margins, styled tables, headers/footers, centered figures/captions). Keep `report/reference.docx` in sync with any layout adjustments; do not delete it.
- Use `<!--PAGEBREAK-->` on its own line for explicit Word page breaks (converted by `report/fit-images.lua` and hidden on GitHub).
- Do not hand-edit files in `report/generated/`: regenerate them with `backend/scripts/report_schema.py`, `backend/scripts/report_tests.py`, and `bin/perf`.
