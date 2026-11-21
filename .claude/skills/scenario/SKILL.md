---
name: scenario
description: Implement one test scenario from section 12 of the specification, test first. Runs only when the user calls /scenario with a scenario number.
argument-hint: <scenario number>
disable-model-invocation: true
---

# Implement scenario $ARGUMENTS

First read `.claude/project-phase`. If it contains `docs`, stop and tell the user: the project is still in the documentation phase and this skill is for the implementation phase. Do not change that file yourself.

## Step 1: read exactly what is needed

1. Find the row of scenario $ARGUMENTS in the table in section 12 of `docs/01-business-spec.md`. Note the "Scenario" and "Expected result" cells word for word.
2. Read the section the "Rule" column points to, and the state table involved (3.1, 3.2 or 3.3).
3. Find the scenario in the table in section 7 of `docs/02-detailed-design.md` to learn its step and service, then read that service's schema section.
4. Find the scenario in section 3 of `docs/03-implementation-plan.md` to learn its test tier.

If part of the scenario belongs to phase 2 (section 12 names these parts), implement only the part for the current phase and say which part is left.

## Step 2: write the test first

1. Write a pytest test marked `@pytest.mark.kb($ARGUMENTS)`. Each clause of "Expected result" is its own assertion; do not merge clauses and do not leave any out.
2. A scenario about a "resent" or "duplicate" message must cover both cases defined at the start of section 12: the same `event_id`, and a new `event_id` for an order id that already has a record.
3. Use a real PostgreSQL, no mocks. Tier 2 scenarios run many times over two connections. Tier 3 scenarios use a real Kafka.
4. Run the test and confirm it fails because the behaviour is missing, not because of a compile or configuration error.
5. Ask the `test-auditor` subagent to audit scenario $ARGUMENTS. Close every gap it reports before implementing. If you think a reported gap is wrong, do not drop it silently: quote the document section that shows why, in the report of step 4.

## Step 3: implement

1. Write the smallest code that makes the test pass, following the module's rules in `.claude/rules/`.
2. Run the scenario's test again, and all tier 1 and tier 2 tests of the module you changed.
3. If the module is Inventory, run the two invariant queries of section 3 of document 02.
4. For a tier 2 scenario, or when the change touches row locking or a transaction boundary, ask the `spec-reviewer` subagent to review the files you changed. Give it the file names and the scenario number, not your own conclusion.

When the documents do not cover a situation you meet, stop and ask the user. Do not choose a behaviour yourself.

## Step 4: report

If the scenario finishes a transaction or a step, update its sections in `report/` (CLAUDE.md, working rules).

Give the user, in Vietnamese: the commands you ran, the test output before and after the implementation, what the subagents reported and what you did about each finding, the files changed, and any part not done. Commit the scenario as one commit (CLAUDE.md, working rules).
