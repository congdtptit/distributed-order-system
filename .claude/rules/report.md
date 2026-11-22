---
paths:
  - "report/**"
---

# Writing and formatting the course report

Applies when creating, editing, or rebuilding files in `report/`.

## Language and style

- Read and follow `.claude/skills/vietnamese-tech-report-writing/SKILL.md` (along with its `references/anti-ai-patterns-vi.md` and `references/before-after-examples.md`) for Vietnamese technical prose, objective tone, and elimination of AI writing tells.
- Focus strictly on proving how the system satisfies the course topic requirements and lecturer template; do not volunteer unprompted weaknesses, missing features, or debug bug-fix stories.
- Keep all system/code identifiers in English as required by `CLAUDE.md` (service names, database/table/column names, Kafka topics, event names, API paths, and upper-case status/reason codes in backticks such as `DANG_GIU`, `CHO_NAU`, `INSUFFICIENT_INGREDIENTS`).
- Place table captions **above** every table (`*Bảng X.Y. ...*`) and figure/diagram captions in the image alt text (`![Hình X.Y. ...](images/...)`), and reference every table and figure directly in the surrounding prose. Do not add a second italic `*Hình X.Y.*` line beneath `![Hình X.Y.](...)`, because Pandoc automatically emits an `ImageCaption` paragraph from the image alt text.
- Do not use Mermaid code blocks in report chapters; render high-resolution PNG diagrams via HTML/SVG and link them as images in `report/images/`.

## Word export (`report/build.sh`)

- `report/build.sh` uses `report/reference.docx` as the Pandoc `--reference-doc` (A4, `Times New Roman`, PTIT margins, styled tables, headers/footers, centered figures/captions). Keep `report/reference.docx` in sync with any layout adjustments; do not delete it.
- Use `<!--PAGEBREAK-->` on its own line for explicit Word page breaks (converted by `report/fit-images.lua` and hidden on GitHub).
- Do not hand-edit files in `report/generated/`: regenerate them with `backend/scripts/report_schema.py`, `backend/scripts/report_tests.py`, and `backend/scripts/report_perf.py`.
