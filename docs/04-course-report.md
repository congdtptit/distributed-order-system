# Course report – the lecturer's template and what the project covers

Revision 1 · 22 Nov 2026 · @Naul · follows documents 01–03

The lecturer sent the report template on 22 Nov 2026: "Mẫu PTTK", a software analysis and design document of the Posts and Telecommunications Institute of Technology (PTIT). The final report of this course project follows it. This document records what the template asks for, where the project already has the material, and what is still missing, so that the missing parts get planned like the code. The template file itself is not in the repository.

The report is written in Vietnamese, following the template; this document, like the rest of the set, is in English. When this document and documents 01–03 disagree, those documents are right.

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
| HLD model (**required**) | The component table and message flows under "Architecture and message flows" in 01; the containers and networks in section 2 of 03 | Partly | A drawing: branches, Kafka with its topics, Inventory ×2, the Kitchen, the replica and the Order Query Service, the screens. Step 8 |
| Function list | Actors and flows in 01 (sections 1, 4–8); the APIs in section 6 of 02 | Partly | One table in the template's columns: modules = branch, Inventory, Kitchen, monitoring, reporting; use cases and transactions from the flows and the API rows. Step 8 |
| Functional design per transaction | The flows (sections 4–8 of 01) and the state tables (3.1–3.4) | Partly | One use-case card per transaction in the template's fields, and an activity diagram for each. Step 8 |
| Databases of the system | Sections 3–5 of 02; the containers in section 2 of 03 | Covered | Inventory DB, Kitchen DB, one branch DB per site (POS01, POS02, ONLINE), the Central Order Replica |
| Overall database diagram (**required**) | The DDL in sections 3–5 of 02 | Missing | One diagram per database, from the migrations. Step 8 |
| Table list and table detail | The DDL and its comments in 02; the live schema | Covered | Generate the Field, Type, Null, Key, Default, Extra tables from `information_schema` of the running databases with a script, so they match the migrations. Step 8 |
| Technology | The technology table in section 2 of 03 | Covered | No mobile application: the Online channel is a web screen. Say so in the report |
| User interface | Planned: step 6b, one screen at a time with `/screen`, which takes a screenshot | Missing | Step 6b, then the screenshots go into the report |
| Test scenarios | The 44 scenarios in section 12 of 01; each test carries `kb(<n>)` | Covered | Export the table with each scenario's state from the test run. Step 8 |
| Distributed testing: model and scenarios (**required**) | Tier 3 on the running cluster with real faults: a stopped consumer process (26), a killed broker (31), Inventory stopped (4), dlq (29); planned: the Kitchen down for 2 hours (25), a branch offline (10, 36), two instances (28, 42), replication cut (55) | Partly | The remaining tier 3 scenarios come with steps 5–7. The report needs a drawing of the test setup (which container is stopped or cut off, and where) |
| Performance testing (**required**) | Nothing yet. Section 6 of 03 has idle resource figures | Missing | Load test with Apache JMeter in a container, as the template does: 250 concurrent users on each chosen API (`POST /orders`, `GET /dishes`, `GET /orders`, `GET /tickets`, `GET /stock`, `GET /reports/summary`), plus resource use from `docker stats` and the time from an order's creation to Reserved at the branch. Needs `POST /orders`, so step 7 |
| Security testing | The template lists Acunetix as a tool but does not mark security testing as required. The lean edition has no authentication (section 15 of 01) | Missing | Optional. A free scanner (OWASP ZAP baseline scan) could stand in for Acunetix. Decision pending (README) |
| Test tools table | pytest, the `chaos` fixture and `bin/chaos`, Vitest, JMeter (planned) | Partly | Fill in with versions once the performance test exists. Step 8 |
| Test environment | Docker Desktop on the developer machine (4 CPUs, 5.8 GB); the containers and their resource use in sections 2 and 6 of 03 | Partly | The template's server table, filled with the machine and the compose setup instead of a server: there is no server. Step 8 |
| Functional result counts | pytest's result (133 backend tests pass on 22 Nov 2026) | Partly | Count per scenario from a test run with JUnit XML output, after step 7. Step 8 |
| Performance result table | | Missing | From the JMeter result files. Step 7 |

## 3. Plan

- **Step 7** gains the performance test: a JMeter test plan in the repository, run in a container on `api-net` against the full cluster, with its result files and `docker stats` kept for the report.
- **A new step 8, report material**, after step 7: the HLD drawing, the function list, the use-case cards and activity diagrams, the database diagrams, the generated table details, the test tables (scenarios, tools, environment, results). Part I and the final assembly of the Vietnamese report are @Naul's, unless Claude is asked to draft them.
- Section 4 of document 03 lists both, and section 7 of 03 counts them in the progress estimate.
