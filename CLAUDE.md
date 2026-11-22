# distributed-order-system

Course project on distributed systems: order taking for a restaurant chain. Branches (POS, Online) create orders and send cancel requests. Inventory reserves, releases and writes off ingredients. The Kitchen cooks, rejects tickets and is the only party that decides cancellations. The services talk through Kafka with at-least-once delivery and no ordering guarantee across topics.

## Language

- Reply to the user in Vietnamese.
- Write every project document in English: everything in `docs/`, this file, and the files under `.claude/`.
- The one exception is the course report in `report/`: Vietnamese, following the lecturer's template (@Naul, 22 Nov 2026). Technical names stay in English and are never translated: component names (Inventory Service, Kafka, outbox…), databases, tables, columns, topics, events, API paths, status and reason codes.
- The user talks about the domain in Vietnamese. The glossary below maps their words to the terms used in the documents.

## Current phase: implementation

- `.claude/project-phase` contains `code`. Only the user changes that file; a hook blocks edits to it.
- The order of work is section 4 of `docs/03-implementation-plan.md`; steps 0 to 6b are done (preparation, the shared `common` module, Inventory, the Kitchen, the branch, the screens) and most of step 7 (reporting and scenario 55, scenario 42 on two instances, the performance test, CI); section 7 there records the progress. Next: the rest of step 7, then the report material (step 8) and phase 2. The final report follows the lecturer's template; document 04 says what it needs. Business code is written one scenario at a time with `/scenario <n>`, screens one at a time with `/screen <name>`.
- The project is built from scratch, with no existing codebase to follow.

## Layout and commands

| Path | Content |
|---|---|
| `docker-compose.yml` | Entry point of Docker Compose: includes the files of `docker/` and declares the networks |
| `docker/` | One file per group of containers: `kafka.yml`, `databases.yml`, `services.yml`, `frontend.yml`, `tools.yml` |
| `backend/` | Python 3.12 uv workspace and its `Dockerfile` (one image for every Python container): `common/`, `order-service/`, `inventory-service/`, `kitchen-service/`, `query-service/`, each with `src/`, `tests/`, `migrations/`; `scripts/` for the init jobs and tools |
| `frontend/` | TypeScript screens: React, Vite, Mantine, TanStack Query |
| `bin/chaos` | Fault injection on the running cluster: a branch offline, a broker or service stopped, replication cut |
| `perf/`, `bin/perf` | The JMeter load test (`perf/plan.jmx`); `bin/perf` runs it and writes `report/generated/hieu-nang.md` |
| `report/` | The course report in Vietnamese, in the lecturer's template: Markdown with Mermaid diagrams, `generated/` from scripts, `build.sh` exports Word. `report/README.md` says how |

Everything runs in Docker; nothing is installed on the host. Source is mounted into the containers, so a code change reloads the service; a change to `pyproject.toml` or `uv.lock` needs `docker compose build`. Section 2 of `docs/03-implementation-plan.md` explains the containers and networks.

| Task | Command |
|---|---|
| Start the core (14 containers, daily work) | `docker compose up -d --wait` |
| Start everything (21 containers: adds inventory-2, pos02, online, Kafka UI, Adminer) | `docker compose --profile full up -d --wait`; needed for the demo and for scenarios 35 and 42 |
| Stop | `docker compose --profile full down` (topics, migrations and replication set themselves up again on the next start) |
| Follow services | `docker compose logs -f kitchen inventory-1 inventory-2` |
| Backend tests, tiers 1 and 2 | `docker compose exec tools pytest -m "not tier3"` |
| Backend tier 3 tests | the `test-runner` subagent, or `docker compose exec tools pytest -m tier3` |
| Backend format, lint, types | `docker compose exec tools ruff format .`, `… ruff check .`, `… pyright` |
| Frontend tests, types, format and lint | `docker compose exec frontend npx --no-install vitest run`, `… tsc --noEmit`, `… biome check --write .` |
| Faults | `bin/chaos offline pos01`, `bin/chaos stop kafka2`, `bin/chaos cut-replication pos01`, `bin/chaos status` |
| Performance test | `bin/perf` (250 users per API; `-Jusers=50` for a lighter run) |
| API types for the screens | `docker compose exec tools python scripts/dump_openapi.py`, then `docker compose exec frontend npm run gen:api` |

| URL | What |
|---|---|
| `http://localhost:5173` | The screens |
| `http://localhost:8080` / `:8081` | Profile `full`: Kafka UI (topics, messages, consumer lag) / Adminer (log in to `inventory-db`, `pos01-db`…, user and password `app`) |
| `http://localhost:8101`, `8102`, `8201`, `8301`–`8303`, `8401` | inventory-1, inventory-2, kitchen, pos01, pos02, online, query (8102, 8302, 8303 with profile `full`); each has `/health` and `/docs` |

Hooks format each edited file (ruff, Biome) and refuse to end a turn while changed code fails pyright, tsc or the tier 1 and 2 tests of its module.

## The documents are the source of truth

| File | Content |
|---|---|
| `docs/01-business-spec.md` | The business: rules BR1–BR12, four state machines, the flows, the test scenarios, deployment assumptions |
| `docs/02-detailed-design.md` | Kafka events, the three DB schemas, the API, the implementation order, the confirmed design choices |
| `docs/03-implementation-plan.md` | Technology, modules, the three test tiers, how Claude Code is used |
| `docs/04-course-report.md` | The lecturer's report template, what the project covers, what is missing for the report |
| `docs/README.md` | Index, pending work, conventions for editing the documents |

- When two documents disagree, the lower-numbered one is right; fix the higher-numbered one.
- Read by section: find the heading with Grep, then read that part. Do not read all of file 01 for one table.
- When the documents do not cover a situation, stop and ask the user. The answer goes into the relevant document, not only into the conversation.
- `docs/archive/` holds frozen Vietnamese originals. Do not read them for answers and do not update them.

## Where to read for what

| Task | Read |
|---|---|
| Order at the branch, status rank, the "Cancel requested" flag | 01 section 3.1; 02 section 5 |
| Order record at the Kitchen, cancellation, origin branch | 01 sections 3.2, 6, 13.2; 02 section 4 |
| Order record at Inventory, stock accounting | 01 section 3.3; 02 section 3 |
| Dish status, version (epoch, seq) | 01 sections 3.4 and 7; 02 sections 3 and 5 |
| Message types, topics, payloads | 02 section 2; 01 section 13.1 |
| Consumers, deduplication, dlq | 01 sections 9 and 13.3; 02 sections 2 (note "The shared consumer") and 3; the code is `backend/common/src/common/`, mapped in `.claude/rules/common.md` |
| What is built, what is next | 03 section 7 |
| What the final report needs | 04; the report itself is `report/` |
| Reason codes (`reason_code`) | 02 section 1; `backend/common/src/common/reasons.py` |
| One test scenario | 01 section 12; its step in 02 section 7; its tier in 03 section 3 |
| What the system promises and does not promise | 01 sections 14 and 15 |
| Dish catalogue, names, seed data | 02 section 1 ("Catalogue and seed data"); the `dishes` table in section 5 |

## Glossary

Status codes in the DB and in code are unaccented Vietnamese in upper case. They are identifiers and stay as they are.

| Term in the documents | Code | Vietnamese, as the user says it |
|---|---|---|
| Branch, Inventory, Kitchen, Management | | Chi nhánh, Kho, Bếp, Quản lý |
| Order, ticket, dish, ingredient, recipe | | đơn, phiếu, món, nguyên liệu, công thức |
| Branch order: Awaiting Inventory, Reserved, Completed, Cancelled, Failed | `CHO_KHO`, `DA_GIU`, `HOAN_TAT`, `DA_HUY`, `THAT_BAI` | Chờ Kho, Đã giữ, Hoàn tất, Đã hủy, Thất bại |
| Kitchen record: (none), Cancel-pending, Queued, Cooking, Completed, Cancelled, Failed | `CHUA_CO`, `HUY_CHO_DON`, `CHO_NAU`, `DANG_NAU`, `HOAN_TAT`, `DA_HUY`, `THAT_BAI` | (chưa có), Hủy chờ đơn, Chờ nấu, Đang nấu, Hoàn tất, Đã hủy, Thất bại |
| Inventory record: Held, Failed, Released, Consumed | `DANG_GIU`, `THAT_BAI`, `DA_TRA`, `DA_DUNG` | Đang giữ, Thất bại, Đã trả, Đã dùng |
| Outcome of one reservation line: released, consumed, wasted | `DA_HOAN`, `DA_DUNG`, `HAO_HUT` | hoàn, đã dùng, hao hụt |
| Dish status: Available, Sold out, Hidden | `CON`, `HET`, `AN` | Còn, Hết, Ẩn |
| Cancel flag at the branch: off, "Cancel requested", "kitchen will not cook" | `KHONG`, `DANG_YEU_CAU`, `BEP_KHONG_NAU` | tắt, Đang yêu cầu hủy, bếp sẽ không nấu |
| Alert kinds: needs review, unmatched command, cancel from wrong branch | `CAN_KIEM_TRA`, `LENH_KHONG_KHOP`, `HUY_SAI_CHI_NHANH` | cần kiểm tra, lệnh không khớp, hủy sai chi nhánh |
| Reserve, release, write off as waste, flag for stock check | | giữ, hoàn, ghi hao hụt, đánh dấu cần kiểm kho |
| Send queue (outbox), entry, "send attempted" flag, local cancel | `attempted` | hàng chờ gửi, gói, cờ "đã thử gửi", hủy cục bộ |
| Origin branch, cancel request, return the stored result | | chi nhánh gốc, yêu cầu hủy, trả lại kết quả cũ |
| Scenario, step, phase, tier | `kb(<n>)` pytest marker | kịch bản, bước, đợt, tầng |

Event names are English as in 02 section 2 (`OrderCreated`, `CancelRequested`, …).

## Working rules

- Every status transition must be in table 3.1, 3.2 or 3.3 of document 01. If it is not there, reject it; do not add one.
- Do not change what a test expects unless you can quote the document section that proves the old expectation wrong.
- Do not use mocks in place of PostgreSQL or Kafka in tests.
- Mark each test `@pytest.mark.kb(<number>)` with the scenario number from 01 section 12.
- Edit the documents following the conventions in `docs/README.md`. A `Stop` hook checks that the document set is still consistent before a turn ends.
- When a step of section 4 of `docs/03-implementation-plan.md` is finished, update its sections in `report/` in the same commit: the function list, the use-case cards and activity diagrams, the database part (`scripts/report_schema.py`), the scenario table (`scripts/report_tests.py`). Section 1 of `report/README.md` lists the sections.
- Git: the remote is `origin`, the default branch is `main`. Commit each part as soon as it is finished and its checks pass (a scenario, a step, a fix, a documents update), without asking; one commit per part (@Naul, 22 Nov 2026). Push only when the user asks. Never commit `.env` files or `.claude/settings.local.json`.

## Twelve things that must not be done

The list from section 9 of document 01, repeated here so that it is always in context.

1. Do not delete order records at the Kitchen or at Inventory.
2. Do not keep the version counter in RAM, and do not use the system clock as a version.
3. Do not assign a snapshot straight into the dish cache.
4. Do not assume the Kitchen receives the order before the cancel request, even when the POS sends them in order.
5. Do not let the Kitchen answer "Cancelled" for an order that has not arrived.
6. Do not recompute the released quantity from the current recipe.
7. Do not block the whole send queue because of one failing entry; do not drop an entry because sending failed.
8. Do not add to stock when a release command matches no reservation record.
9. Do not cancel locally an order whose create-order entry has been attempted, even if that attempt reported an error.
10. Do not treat a Kafka acknowledgement as Inventory having received the order.
11. Do not let the Kitchen ignore a Failed message for an order it has no record of.
12. Do not reserve an ingredient that is flagged for stock check, even when available stock is sufficient.
