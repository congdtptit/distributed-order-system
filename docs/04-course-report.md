# Course report – the lecturer's template and what the project covers

Revision 2 · 22 Nov 2026 · @Naul · follows documents 01–03

The lecturer sent the report template on 22 Nov 2026: "Mẫu PTTK", a software analysis and design document of the Posts and Telecommunications Institute of Technology (PTIT). The final report of this course project follows it. This document records what the template asks for, where the project already has the material, and what is still missing, so that the missing parts get planned like the code. The template file itself is not in the repository.

The report itself is in `report/`. When this document and documents 01–03 disagree, those documents are right.

## Changes in revision 2

| Section | Change | Reason |
|---|---|---|
| Introduction, 3 | The report is written in Vietnamese in `report/`, as Markdown exported to Word, and grows with each step instead of waiting for step 8; technical names stay in English | @Naul, 22 Nov 2026: the report must follow the template, and its parts are written while each step is fresh. @Naul chose Vietnamese with untranslated technical names, and Markdown in the repository exported to Word |
| 2 | States after the first version of `report/`: HLD, function list, use cases of the built transactions, database part, scenario table and distributed test model now exist | Written on 22 Nov 2026 |

## How the report is made

- **Language:** Vietnamese, the language of the template. Technical names are never translated: component names, databases, tables, columns, topics, events, API paths, status and reason codes stay as they are in documents 01–03 and in the code.
- **Format:** Markdown files in `report/`, one per part of the template, with diagrams in Mermaid. `report/build.sh` joins them, draws the diagrams and exports `report/build/bao-cao.docx` with pandoc, all in Docker. The page layout of the template (font, margins) comes later with a `reference.docx` (step 8).
- **Generated parts:** the database diagrams and the table details come from the running databases (`backend/scripts/report_schema.py`); the scenario table and the result counts come from a full pytest run (`backend/scripts/report_tests.py`, each test records its `kb(<n>)` in the JUnit XML). The Vietnamese wording of the scenarios is taken from the frozen original of specification v1.5 in `docs/archive/`; the scenarios have not changed since.
- **When:** each step of section 4 of document 03 updates its parts of the report in the same commit (CLAUDE.md, working rules).

## 1. What the template asks for

The template's headings are numbered inconsistently (Part II appears twice); the table follows its table of contents. Items the template highlights as required are marked **required**.

| Part | Section | What it asks for |
|---|---|---|
| Cover | | PTIT header; title "Software analysis and design document – system …" |
| I. Requirements survey | I. The unit today | How the customer works now |
| | II. Solutions on the market, in Vietnam and abroad | One page |
| | III. Conclusion | Strengths and gaps of existing solutions against the customer's needs, hence why a custom solution is needed |
| II. Analysis and design | (opening) | **Required:** a high-level design (HLD) model of the system |
| | I. Function list | One table: number, module, use case, transaction, main actor |
| | II. Functional design | Per transaction: use case name, description ("actor + transaction"), main and secondary actor, pre-condition, post-condition, sequence of events, non-functional requirements, activity diagram |
| | III.1 Databases of the system | Table: number, database, note |
| | III.2 Detailed database design | **Required:** an overall database diagram. Then a table list with a description of each table, and per table its columns as Field, Type, Null, Key, Default, Extra |
| III. Building the system | I. Technology | System architecture (open source), back-end platform, DBMS, web application platform, mobile application platform |
| | II. User interface | Each screen described, with its picture |
| IV. Testing and evaluation | I.1 Test scenarios | The scenarios |
| | I.2.1 Purpose | **Required:** functional testing covers the distributed properties: a full model and scenarios to test distribution, fault tolerance and recovery. **Required:** performance testing: resource use and how well the software meets demand under stated conditions, and conformance to performance standards |
| | I.2.2 Tools | Table: activity, tool or browser, vendor, version. The example lists browsers and Excel for functional testing, Apache JMeter 5.6 for performance testing, Acunetix 13 for security testing |
| | I.2.3 Test environment | Table: system, host name, IP address, server configuration, installed software |
| | I.2.4 Results | Functional: passed, failed, not testable, total. Performance: the functions put under load (the example: 250 concurrent users on each of 15 functions, 3,750 requests in all) and the aggregate: samples, average, minimum and maximum response time, error rate, throughput |

## 2. What the project covers

State: **covered** (the material exists and only needs reformatting into the template), **partly**, **missing**.

| Template item | Where the material is | State | What is left, and when |
|---|---|---|---|
| Part I: the unit, the market, the conclusion | Nothing yet. Section 1 of the specification gives the purpose and scope | Missing | Writing and research, not code: the restaurant chain's situation, POS and order-management products in Vietnam and abroad, and why they do not fit the offline and cancellation rules (BR5–BR9). @Naul to decide who writes it; Claude can draft it on request |
| HLD model (**required**) | `report/02-phan-tich-thiet-ke.md`, from the component table in 01 and section 2 of 03 | Covered | The drawing's layout can be tidied in step 8 |
| Function list | `report/02-phan-tich-thiet-ke.md`, every transaction of phases 1 and 2 | Covered | Kept in line as the APIs are built |
| Functional design per transaction | `report/02-phan-tich-thiet-ke.md`: cards and activity diagrams for the 11 transactions of Inventory and the Kitchen built so far | Partly | The branch's transactions in step 6, cancel requests in step 5, alerts and the report in step 7, dish status in phase 2 |
| Databases of the system | Sections 3–5 of 02; the containers in section 2 of 03 | Covered | Inventory DB, Kitchen DB, one branch DB per site (POS01, POS02, ONLINE), the Central Order Replica |
| Overall database diagram (**required**) | `report/02-phan-tich-thiet-ke.md` (overview of the six databases and how data moves between them) and one ER diagram per database in `report/generated/csdl.md` | Covered | Regenerate after each migration |
| Table list and table detail | `report/02-phan-tich-thiet-ke.md` (23 tables with descriptions) and `report/generated/csdl.md` (Field, Type, Null, Key, Default, Extra) | Covered | Regenerate after each migration |
| Technology | `report/03-xay-dung.md` | Covered | |
| User interface | Planned: step 6b, one screen at a time with `/screen`, which takes a screenshot | Missing | Step 6b, then the screenshots go into the report |
| Test scenarios | `report/generated/kiem-thu.md`, from a full test run: 20 of 44 pass on 22 Nov 2026 (6 and 48 counting their phase 1 parts) | Covered | Regenerate after each step |
| Distributed testing: model and scenarios (**required**) | `report/04-kiem-thu.md`: the test setup drawing and a table of the faults injected (26, 29, 31, 4, 24 done) | Partly | The Kitchen down for 2 hours (25), a branch offline (10, 12, 36), two instances (28, 42), replication cut (55) come with steps 5–7 |
| Performance testing (**required**) | Nothing yet. Section 6 of 03 has idle resource figures | Missing | Load test with Apache JMeter in a container, as the template does: 250 concurrent users on each chosen API (`POST /orders`, `GET /dishes`, `GET /orders`, `GET /tickets`, `GET /stock`, `GET /reports/summary`), plus resource use from `docker stats` and the time from an order's creation to Reserved at the branch. Needs `POST /orders`, so step 7 |
| Security testing | The template lists Acunetix as a tool but does not mark security testing as required. The lean edition has no authentication (section 15 of 01) | Missing | Optional. A free scanner (OWASP ZAP baseline scan) could stand in for Acunetix. Decision pending (README) |
| Test tools table | `report/04-kiem-thu.md` | Partly | JMeter's version in step 7 |
| Test environment | `report/04-kiem-thu.md`: the developer machine and the compose setup in the template's server table (there is no server) | Covered | Resource figures under load in step 7 |
| Functional result counts | The summary table at the end of `report/generated/kiem-thu.md` (133 tests, 0 failed on 22 Nov 2026) | Covered | Regenerate after each step |
| Performance result table | | Missing | From the JMeter result files. Step 7 |

## 3. Plan

- **Every step** updates its parts of `report/` when it is done (section "How the report is made").
- **Step 7** gains the performance test: a JMeter test plan in the repository, run in a container on `api-net` against the full cluster, with its result files and `docker stats` kept for the report.
- **Step 8, report material,** is now what is left once the steps are done: tidying the diagrams, the page layout of the template (`reference.docx`), and the final read-through. Part I and the cover are @Naul's, unless Claude is asked to draft them.
- Section 4 of document 03 lists both, and section 7 of 03 counts them in the progress estimate.
