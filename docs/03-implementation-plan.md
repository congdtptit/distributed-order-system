# Implementation plan – architecture, testing and how to use Claude Code

Revision 6 · 21 Nov 2026

This document says how to implement business specification v1.5 and the detailed design (revision 4): what to build with, how to test, in what order to work, and how to use Claude Code. The project is in the documentation phase and no code has been written. Where this document disagrees with the specification or the detailed design, those two documents are right.

## Changes in revision 6

| Section | Change | Reason |
|---|---|---|
| 2 | New `web` module: a TypeScript frontend (React, Vite, Mantine, TanStack Query) with types generated from the services' OpenAPI; a fourth structural principle, "the screens decide nothing" | The specification describes screen behaviour (01 sections 6–8) but no document said who builds the screens. @Naul chose TypeScript on 21 Nov 2026 |
| 3 | How the `web` module is tested | HTTP stubs are allowed there; the no-mock rule covers PostgreSQL and Kafka |
| 4 | New step 6b for the screens; the Management screen joins step 7; blocking Sold-out dishes on screen joins phase 2 | The screens need the APIs of all three sides. Point 5 of the design makes the screen the only place that blocks a Sold-out dish |
| 5.3, 5.6, 5.7 | The format hook, the test gate and CI also cover `web`; new rows for `.claude/rules/web.md` and the `/screen` skill | A second language needs its own checks |

## Changes in revision 5

| Section | Change | Reason |
|---|---|---|
| 1 | Three of the five points in section 11 of the specification are confirmed: BR12 with the Consumed message, local cancel under BR9, and blocking flagged ingredients under BR6. BR12 is now named among the points that change behaviour | @Naul agreed on 21 Nov 2026. Revision 4 named only BR9 and BR6, although BR12 decides the Inventory schema and the event catalogue |

## Changes in revision 4

| Section | Change | Reason |
|---|---|---|
| 5.5 | States which work goes to subagents and which stays in the main session; lists the four subagents; the review before the demo is three parallel runs of `spec-reviewer`, with Agent Teams as an option | The roles were only sketched before, and no subagent was tied to a point in the workflow |
| 5.2, 5.3, 5.6 | The test audit is now the `test-auditor` subagent, called in step 2 of `/scenario`; `spec-reviewer` is called from step 3 | An audit placed inside the loop runs every time; a separate script is easy to forget |
| 5.7 | New rows for `test-auditor` and `test-runner` | `test-auditor` was created on 21 Nov 2026; `test-runner` waits for step 0 |
| 1, 6 | Point 12 of the design is confirmed | @Naul agreed on 21 Nov 2026 |
| 4, 5.7 | The git repository exists; step 0 no longer creates it | Set up on 21 Nov 2026, ahead of step 0, at the user's request |
| 5.6 | CI is laid out as four GitHub Actions workflows; `docs` is created; there is no continuous deployment | The repository is on GitHub, and the project has no server to deploy to |

## Changes in revision 3

| Section | Change | Reason |
|---|---|---|
| 1, 2, 6 | The project is built from scratch in Python 3.12; every reference to a B5 baseline is gone | There is no B5 codebase, and @Naul chose Python on 21 Nov 2026 |
| 2, 4 | Management reporting (the Order Query Service and replication) is now work of this project | There is no existing reporting service to reuse |
| 3, 5 | Tests carry a pytest marker with the scenario number; the checkpoints name the Python tools | Follows from the language choice |

## Changes in revision 2

| Section | Change | Reason |
|---|---|---|
| 3 | The three test tiers now cover 44 scenarios; the extra test about a recipe change is gone | Specification v1.5 added scenarios 48–55, and scenario 49 is that test |
| 5 | New section 5.7 records which parts of the Claude Code configuration exist and which are pending | The parts that do not depend on the technology were created on 21 Nov 2026 |
| Whole file | Translated into English and renamed to `03-implementation-plan.md` | Project documents are written in English from 21 Nov 2026 |

## 1. What must be done before coding

- **Close the open points.** All twelve points in section 8 of the detailed design were confirmed on 21 Nov 2026. Of the five points in section 11 of the specification, the three that change behaviour (BR12 with the Consumed message, local cancel under BR9, blocking flagged ingredients under BR6) were confirmed on 21 Nov 2026. The two still open, the parameters of section 10 and the list of cancel reasons, live in configuration and do not block progress.
- **Move the project to the implementation phase.** The user changes `.claude/project-phase` from `docs` to `code`. Until then Claude Code is blocked from creating code.

Nothing else blocks step 0: the language is settled (section 2) and there is no existing codebase to align with.

## 2. Deployment architecture

### Technology

The project is built from scratch; there is no existing codebase to follow. Python was chosen on 21 Nov 2026 (@Naul). The libraries below are proposals; their versions and exact settings are verified in step 0.

| Part | Choice | Reason |
|---|---|---|
| Language | Python 3.12 | Light enough to run seven service processes beside three brokers and six databases on one machine; short code that the team can read and explain; the SQL trial-run script is already Python and seeds the test suite |
| HTTP | FastAPI with Uvicorn | Small, with typed request models; enough for the few endpoints in section 6 of the design |
| DB access | psycopg 3 with plain SQL, no ORM | The specification and the design are written directly in SQL (`FOR UPDATE`, `ON CONFLICT`, `SAVEPOINT`, conditional UPDATE); an ORM hides exactly the places that need control |
| Schema migrations | Numbered SQL files applied by a small runner in `common` | The DDL in the design is already SQL, so there is no extra tool to learn |
| Kafka in the application | `confluent-kafka`, with a hand-written consumer loop following the five steps of section 13.3 of the specification | It exposes the settings the specification requires (`acks=all`, `enable.idempotence`, auto-commit off, pattern subscription); a hand-written loop makes it easy to insert a stop point between the DB commit and the offset commit for scenario 26 |
| Infrastructure | Docker Compose: Kafka in KRaft mode with 3 brokers, one PostgreSQL container per DB | Matches section 13.6 of the specification |
| Central Order Replica | PostgreSQL logical replication, one subscription per branch (section 5 of the design) | Asynchronous replication that the database already provides; no extra service to write |
| Testing | pytest, Testcontainers for Python, and Toxiproxy to cut the network | Tests run against a real PostgreSQL and a real Kafka |
| Code quality | Ruff for formatting and linting, Pyright for type checking | Python has no compiler to catch type errors, so the type checker runs together with the tests |
| Frontend language | TypeScript, chosen on 21 Nov 2026 (@Naul) | Typed against the same API contract as the services |
| Frontend framework | React with Vite, React Router | Common, well documented, no server-side rendering needed for a demo |
| UI components | Mantine | Tables, badges, modals and notifications that look finished without designing them; keeps the frontend plain |
| Server state | TanStack Query, polling every 2 seconds on the screen in view | Statuses arrive asynchronously through Kafka, so screens must refresh; polling is enough and needs no WebSocket |
| API types | `openapi-typescript`, generated from each service's FastAPI OpenAPI document | A change to a request or response breaks the frontend build instead of the demo |
| Frontend quality | Biome for formatting and linting, `tsc --noEmit`, Vitest with Testing Library and MSW | One tool for format and lint; tests run without a browser |

The hardest parts of the project, races and deduplication, are solved by row locks and transactions inside PostgreSQL, so they do not depend on the language.

### Modules

| Module | Content |
|---|---|
| `common` | Message envelope, outbox relay, deduplicating consumer loop, sending to the dlq and writing `alerts`, replaceable clock |
| `order-service` | One codebase for both POS and Online, told apart by `BRANCH_ID` |
| `inventory-service` | Table 3.3, stock accounting, dish status |
| `kitchen-service` | Table 3.2, the three kitchen staff buttons |
| `query-service` | The Order Query Service: Management reporting read from the Central Order Replica (sections 5 and 6 of the design) |
| `web` | The screens, in TypeScript: branch (POS and Online), Kitchen, Inventory, monitoring (Flow D), Management, and a demo page with a branch and the Kitchen side by side. Labels are in Vietnamese, using the glossary in `CLAUDE.md` |
| `infra/`, `e2e/` | Compose files, topic creation script, end-to-end scenarios |

### Four structural principles

- **The handler is separate from the consumer loop.** A handler receives one message and one DB transaction and knows nothing about Kafka. A test can therefore decide the order in which messages arrive, and most scenarios need no real Kafka.
- **The clock is replaceable.** Inventory and the branch read time through a clock object, so that scenarios 15, 16, 21 and 25 do not wait for real time.
- **One entry point at the Kitchen.** The consumer and the three buttons call the same row-locking function, as section 4 of the detailed design requires.
- **The screens decide nothing.** `web` calls only the APIs in section 6 of the design and shows the statuses the services return. It never infers a status, and it treats a 409 as the normal outcome of a race: it reloads the item and says so. The one rule that lives only on screen is blocking a Sold-out dish while the data is fresh (point 5 in section 8 of the design). In development the Vite server forwards `/api/<service>/…` to each service; for the demo an nginx container serves the built files and forwards the same paths, so the browser never needs CORS.

### Notes for setting up the infrastructure

- **Create topics with a script**, with the partition counts of point 6 in section 8 of the design, `replication.factor=3` and `min.insync.replicas=2`. Do not rely on auto-create.
- **Kafka's internal topics also need 3 replicas** (`offsets.topic.replication.factor=3`). Otherwise stopping one broker in scenario 31 can stall the consumers.
- **A pattern subscription sees a new topic only after a metadata refresh**, 5 minutes by default. Create every branch's topics before starting the services to avoid the wait.
- **Simulate network loss** by disconnecting the branch container from the Kafka network, or with Toxiproxy in tests.

## 3. Test strategy

Section 12 of the specification requires an automated test for every scenario. The 44 scenarios fall into three tiers according to what they need to run.

| Tier | How it runs | Scenarios |
|---|---|---|
| 1. Handler and a real PostgreSQL | The test calls handlers in the order it wants | 1, 2, 5–9, 15, 16, 19–23, 27, 30, 33–35, 39, 43, 44, 48–50, 53, 54 (27 scenarios) |
| 2. Races | Two threads on two connections, repeated many times | 3, 28, 37, 42, 51, 52 |
| 3. Real Kafka, replication and fault injection | Stopping containers, cutting the network; slow, so run separately | 4, 10, 12, 18, 24–26, 29, 31, 36, 55 |

Conventions for every test:

- Each test carries the marker `@pytest.mark.kb(<number>)` with its scenario number (written `KB-<number>` in the documents), so that a scenario-to-test table can be produced.
- No mocks in place of PostgreSQL or Kafka. A mock makes a test pass without proving anything about row locks and transactions.
- After every Inventory test, run the two invariant queries in section 3 of the detailed design.
- Each scenario has a handler-level version at its own step and, if it needs several services, an end-to-end version that runs after step 6 (section 7 of the design).
- The `web` module is tested with Vitest: each screen's display rules from the specification (for example, the Cancel button is hidden when the order is terminal) against API responses stubbed with MSW. Stubbing HTTP is allowed here; the no-mock rule covers PostgreSQL and Kafka. Screens are not scenario tests and carry no `kb` marker; the scenarios stay proven at the service level.

Section 9 of the detailed design records the SQL that was trial-run while the documents were written. Those runs do not replace this test suite.

## 4. Order of work

The order follows the steps and phase 2 in section 7 of the detailed design; the scenarios of each step are listed there. This plan adds a preparation step at the start and a screens step (6b) after step 6, folds reporting into an integration step at the end, and says how to work with Claude Code at each step.

| Step | Content | How to work with Claude Code |
|---|---|---|
| 0. Preparation | Project skeleton, compose files, topic creation script, CI, the remaining Claude Code configuration of section 5.7 | One session in plan mode; a person reviews closely |
| 1. Shared | The `common` module | One session; reviewed by a reviewer running in a fresh context |
| 2–3. Inventory | Reserve, release, waste, consumed, the stock-check flag | A separate worktree, one scenario at a time |
| 4–5. Kitchen | Table 3.2, cancel requests, origin branch | A separate worktree, one scenario at a time |
| 6. Branch | Send queue, local cancel, applying messages by rank | A separate worktree, one scenario at a time |
| 6b. Screens | The `web` screens for the branch, the Kitchen, Inventory and monitoring, and the demo page, against the APIs of steps 2–6 | One session, one screen at a time with the `/screen` skill |
| 7. Integration | Tier 3 scenarios, Flow D (`/monitor`, `/alerts`), the Order Query Service and replication (scenario 55), the Management screen | One main session; slow test runs are delegated to a subagent |
| Phase 2 | Flow C, including blocking a Sold-out dish on the branch screen while the data is fresh and the "may be sold out" warning when it is stale | One session, scenarios 18–21 |
| Demo | Scenarios 1, 3, 4, 10, 36 on all services | One repeatable demo script |

The detailed design allows Inventory and the branch to proceed in parallel after step 1. This plan proposes running the Kitchen in parallel as well: the message contract is fixed by the design, and the Kitchen's handler-level tests need neither Inventory nor the branch.

## 5. How to use Claude Code

For this project the hard part of using AI is keeping the code in line with three state tables and 44 scenarios across many sessions. The approach is to turn the documents into something a machine can check first, and only then let Claude write code one scenario at a time. Section 5.7 records what has already been set up.

### 5.1 Context

- **This document set is the source.** Claude reads it section by section and does not load a whole document into every session.
- **`CLAUDE.md`** stays under 200 lines: build and test commands, the document map, the glossary, and the twelve prohibitions from section 9 of the specification.
- **`.claude/rules/`** uses `paths:` per module, and each file points to the sections to read: `kitchen-service/**` to table 3.2 and section 4 of the design; `inventory-service/**` to table 3.3 and section 3; `order-service/**` to table 3.1 and section 5.
- **Where the documents are silent**, Claude stops and asks; the answer is written into the relevant document, not left in the conversation.

### 5.2 The per-scenario loop

A `/scenario <number>` skill, callable only by the user, prescribes four steps:

1. Read the scenario row in section 12 of the specification and the section its "Rule" column points to.
2. Write a test marked `@pytest.mark.kb(<number>)` that asserts every clause of "Expected result", run it, and confirm it fails for the right reason. Then the `test-auditor` subagent audits the test, and its gaps are closed before any implementation.
3. Implement, run again, and give the output as evidence. For a tier 2 scenario, or a change to row locking or a transaction boundary, the `spec-reviewer` subagent reviews the changed files.
4. One commit for that scenario.

At the start of each step of section 4, use plan mode to produce a plan. Clear the context between groups of scenarios.

### 5.3 Checkpoints

| Mechanism | What it catches |
|---|---|
| `PostToolUse` hook | Formats a file after each edit: `ruff format` for Python, Biome for TypeScript |
| `PreToolUse` hook | Editing an applied migration; `DELETE` on the order tables of the Kitchen and Inventory; turning offset auto-commit on |
| `Stop` hook | The turn cannot end while tier 1 and 2 tests of the changed module are red or Pyright reports an error; for `web`, while `tsc` or Vitest fails |
| `test-auditor` subagent, read-only | A test that leaves a clause of "Expected result" unasserted; a race test that runs on one connection; a mock |
| `spec-reviewer` subagent, read-only | A status transition missing from tables 3.1–3.3; a diff that touches what a test expects |
| `/invariants` skill | Negative stock, reserved quantity out of line, a reservation leaving Held twice |

### 5.4 Where AI is likely to go wrong on this project

- **Changing the test to make it pass instead of fixing the code.** Rule: do not change what a test expects without quoting the document section that justifies it.
- **Code that is right sequentially and wrong concurrently.** The tier 2 scenarios must run many times, and a person should read the row-locking code.
- **Assuming a message order.** Every handler must be correct for any arrival order; section 2 of the design has the example of `CancelPending` arriving after `OrderFailed`.
- **Filling in where the documents are silent.** See section 5.1.

### 5.5 Several agents

Implementation stays in the main session, where the user sees every step and can answer when the documents are silent. A subagent gets only three kinds of work: a review that must not be anchored on the implementer's reasoning, an audit against a fixed checklist, and a run whose output is long.

| Subagent | Job | When it runs | Access |
|---|---|---|---|
| `doc-auditor` | Reviews the specification for contradictions and untested behaviour | After every version bump of the specification | Read-only |
| `test-auditor` | Checks that the test of a scenario asserts every clause of "Expected result", at the right tier, without mocks | Step 2 of `/scenario`, before implementing; once for all scenarios before the demo | Read-only |
| `spec-reviewer` | Reviews code against tables 3.1–3.3, the twelve prohibitions, the lock order and the transaction boundaries | Step 3 of `/scenario` for tier 2 scenarios and locking changes; at the end of each step of section 4; before a worktree is merged | Read-only |
| `test-runner` | Runs the slow tier 3 tests and returns only the failures | Step 7 | Runs commands. Created in step 0, when the test commands exist |

There is no implementing subagent per module. A subagent cannot ask the user a question, knows only what its brief says and hands back only a summary. For code that has to follow three state tables, that costs more than it saves.

- **Three parallel worktrees** for Inventory, the Kitchen and the branch after step 1. These are three sessions started by the user, not subagents. Each session owns one module; changes to `common` or to the message contract are made on the main branch only.
- **Review before the demo** from three angles: deduplication (BR4, BR8, BR12), races (BR7, BR9) and stock accounting. Run `spec-reviewer` three times in parallel, one angle per run. Agent Teams can do the same with teammates that challenge each other's findings; it is experimental and uses far more tokens than a normal session, so it is optional.

### 5.6 Automation

CI runs on GitHub Actions, one workflow file per row in `.github/workflows/`.

| Workflow | Runs on | What it runs | State |
|---|---|---|---|
| `docs` | Every push to `main` and every pull request | The document consistency check, the same script as the `Stop` hook | Created |
| `ci` | Every push to `main` and every pull request | `ruff format --check`, `ruff check`, Pyright, then the tier 1 and tier 2 tests; PostgreSQL is started by Testcontainers. A second job for `web`: Biome, `tsc --noEmit`, Vitest | Step 0, when the skeleton and the commands exist |
| `nightly` | Once a night, and on manual start | The tier 3 tests with a real Kafka; they are slow and can be flaky, so they do not block a pull request | Step 7 |
| `review` | Every pull request | Review by `claude-code-action`, with a `REVIEW.md` holding the twelve prohibitions, a turn limit and a timeout | After step 1. It needs an API key stored as a repository secret |

There is no continuous deployment: the system is demonstrated on one machine with Docker Compose and has no server to deploy to. In its place, `ci` gains a job in step 7 that builds every service image and starts the compose file, so that the demo setup cannot break unnoticed.

- **Test quality audit:** done by the `test-auditor` subagent inside `/scenario` (section 5.5). Before the demo, one run over every scenario gives the scenario-to-test table.
- **Not needed for this project:** an MCP server (`psql` and the Kafka CLI through Bash are enough), the Agent SDK and OpenTelemetry.

### 5.7 Current state of the configuration

The parts that do not depend on the code were created on 21 Nov 2026. The rest belongs to step 0, when the project skeleton exists.

| Part | File | State |
|---|---|---|
| Git repository | `origin` on GitHub, branch `main`; `.gitignore`, `.gitattributes` | Created. It holds the documents and the Claude Code configuration; no code yet |
| CI for the documents | `.github/workflows/docs.yml` | Created. It first runs when the repository is pushed |
| Shared context | `CLAUDE.md` | Created. No build or test commands yet |
| Conventions for editing the documents | `.claude/rules/docs.md` | Created, in use |
| Rules per module | `.claude/rules/common.md`, `inventory.md`, `kitchen.md`, `order-service.md` | Created. Their `paths` use the module names in section 2; change them if the layout changes in step 0 |
| Document consistency check | `/doc-check` skill and the `Stop` hook | Created, in use |
| Blocking code during the documentation phase | `PreToolUse` hook and `.claude/project-phase` | Created, in use. Change the file's content to `code` when implementation starts |
| The per-scenario loop | `/scenario` skill | Created. It refuses to run until the phase is `code`. It calls `test-auditor` and `spec-reviewer` |
| Independent review of the specification | `doc-auditor` subagent | Created |
| Auditing a test against its scenario | `test-auditor` subagent | Created. Useful once there are tests |
| Reviewing code against the specification | `spec-reviewer` subagent | Created. Useful once there is code |
| Running the slow tests | `test-runner` subagent | Not created. It needs the test commands of step 0 |
| Formatting, the test gate at `Stop`, blocking edits to applied migrations, blocking `DELETE` and auto-commit | Hooks | Not created. They need the project skeleton and the installed tools |
| `/invariants` skill, the `ci`, `nightly` and `review` workflows of section 5.6 | | Not created. Step 0 and later |
| Rules for the screens | `.claude/rules/web.md`, `paths: web/**` | Not created. Step 0, with the `web` skeleton |
| Building one screen | `/screen <name>` skill: read the specification section of the screen, list every state it must show, build it, test its display rules, take a screenshot for the user | Not created. Step 6b |

## 6. Open risks

- **Python catches fewer errors before the code runs.** Type hints checked by Pyright and the scenario tests have to make up for the missing compiler; both run before a turn ends.
- **Replication and reporting are designed but not trial-run.** Point 12 in section 8 of the design was agreed on 21 Nov 2026, but logical replication was not part of the SQL trial runs. Try it on two PostgreSQL containers in step 0, before step 7 depends on it.
- **How Kafka assigns partitions to the two Inventory instances** needs a trial run (point 6 in section 8 of the design). Scenario 42 therefore takes its handler-level test as the main one.
- **Resources of the demo machine.** With two POS sites, one machine has to run three brokers, six PostgreSQL databases and seven service processes at once; measure early, in step 0.
- **A second toolchain.** Node and npm run in their own container, like the Python tools. Their `node_modules` stay inside the container, so the editor sees the TypeScript types only when the project is opened in the dev container.
- **Tier 3 scenarios tend to be flaky.** They depend on when containers stop and start; they need explicit wait conditions instead of waiting on time.
