#!/usr/bin/env python3
"""Check that the documents in docs/ agree with each other.

Exits 0 with a one-line summary when they do; exits 1 and lists each mismatch otherwise.
Standard library only. Run from anywhere:
    python3 .claude/skills/doc-check/scripts/check_docs.py [project_root]
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[4]
DOCS = ROOT / "docs"
SPEC = DOCS / "01-business-spec.md"
DESIGN = DOCS / "02-detailed-design.md"
PLAN = DOCS / "03-implementation-plan.md"
README = DOCS / "README.md"

errors = []


def err(msg):
    errors.append(msg)


def read(path):
    if not path.exists():
        err(f"missing file {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def section(text, prefix):
    """Return the level-2 section whose heading starts with prefix, e.g. '12.'."""
    m = re.search(rf"^## {re.escape(prefix)}.*?(?=^## |\Z)", text, re.S | re.M)
    return m.group(0) if m else ""


def numbers(cell):
    """Scenario numbers in a table cell; understands ranges like '5–9', ignores text in parentheses."""
    cell = re.sub(r"\([^)]*\)", "", cell)
    out = []
    for a, b in re.findall(r"(\d+)(?:\s*[–-]\s*(\d+))?", cell):
        out.extend(range(int(a), int(b or a) + 1))
    return out


def last_cell(row):
    return row.strip().strip("|").split("|")[-1]


# ---------- 1. Markdown structure of every file ----------
def check_structure(path):
    name = path.relative_to(ROOT)
    lines = read(path).splitlines()
    in_code, width = False, None
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith("|"):
            n = len(re.sub(r"`[^`]*`", "", line).strip().strip("|").split("|"))
            if width is None:
                width = n
            elif n != width:
                err(f"{name}:{i}: misaligned table row ({n} columns, the table starts with {width})")
        else:
            width = None
    if in_code:
        err(f"{name}: a code block is not closed")
    for target in re.findall(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)", "\n".join(lines)):
        if not target.startswith("http") and not (path.parent / target).exists():
            err(f"{name}: broken link to {target}")


for md in sorted(DOCS.glob("*.md")):
    check_structure(md)

spec, design, plan, readme = read(SPEC), read(DESIGN), read(PLAN), read(README)

# ---------- 2. Document 01 ----------
m = re.search(r"^# Business specification v(\d+\.\d+)", spec, re.M)
spec_version = m.group(1) if m else None
if not spec_version:
    err("01: cannot read the version in the title")

brs = re.findall(r"^\| (BR\d+) \|", section(spec, "2."), re.M)
if brs != [f"BR{i}" for i in range(1, 13)]:
    err(f"01 section 2: expected BR1–BR12 in order, found {brs}")

sec12 = section(spec, "12.")
scenario_ids = [int(x) for x in re.findall(r"^\| (\d+) \|", sec12, re.M)]
scenarios = set(scenario_ids)
if len(scenario_ids) != len(scenarios):
    dup = sorted({x for x in scenario_ids if scenario_ids.count(x) > 1})
    err(f"01 section 12: duplicate scenario numbers {dup}")
if not scenarios:
    err("01 section 12: no scenario rows found")
m = re.search(r"the table has (\d+) scenarios", sec12)
if not m:
    err("01 section 12: the opening lacks the sentence 'the table has N scenarios'")
elif int(m.group(1)) != len(scenarios):
    err(f"01 section 12: the opening says {m.group(1)} scenarios, the table has {len(scenarios)}")

# ---------- 3. Document 02 ----------
m = re.search(r"^Revision (\d+)", design, re.M)
design_rev = m.group(1) if m else None
if not design_rev:
    err("02: cannot read the revision number on the first line")
m = re.search(r"follows business specification v(\d+\.\d+)", design)
if not m:
    err("02: the first line lacks 'follows business specification vX.Y'")
elif m.group(1) != spec_version:
    err(f"02: says it follows specification v{m.group(1)}, but 01 is v{spec_version}")

sec2 = section(design, "2.")
event_types = set(re.findall(r"^\| `([A-Z][A-Za-z]+)` \| `", sec2, re.M))
m = re.search(r"has (\d+) event types", sec2)
if not m:
    err("02 section 2: the opening lacks 'has N event types'")
elif int(m.group(1)) != len(event_types):
    err(f"02 section 2: says {m.group(1)} event types, the table has {len(event_types)}")

sec7 = section(design, "7.")
steps = set()
for row in re.findall(r"^\| (?:\d+|Phase 2) \|.*\|$", sec7, re.M):
    steps |= set(numbers(last_cell(row)))
if steps != scenarios:
    if scenarios - steps:
        err(f"02 section 7: no step assigned to scenarios {sorted(scenarios - steps)}")
    if steps - scenarios:
        err(f"02 section 7: mentions scenarios that are not in 01 section 12: {sorted(steps - scenarios)}")
m = re.search(r"with (\d+) scenarios; phase 2 is Flow C with (\d+) scenarios", sec7)
if not m:
    err("02 section 7: the opening lacks 'with N scenarios; phase 2 is Flow C with M scenarios'")
elif int(m.group(1)) + int(m.group(2)) != len(scenarios):
    err(f"02 section 7: the opening says {m.group(1)} + {m.group(2)} scenarios, 01 has {len(scenarios)}")

sec8 = section(design, "8.")
points = [int(x) for x in re.findall(r"^- \[[ x]\] \*\*(\d+)\.", sec8, re.M)]
if not points or points != list(range(1, len(points) + 1)):
    err(f"02 section 8: points are not numbered consecutively: {points}")
design_open = len(re.findall(r"^- \[ \]", sec8, re.M))

# ---------- 4. Document 03 ----------
sec3 = section(plan, "3.")
tier_rows = re.findall(r"^\| [123]\. .*\|$", sec3, re.M)
if len(tier_rows) != 3:
    err(f"03 section 3: expected exactly three tier rows, found {len(tier_rows)}")
else:
    tiers = [numbers(last_cell(r)) for r in tier_rows]
    flat = [x for t in tiers for x in t]
    if len(flat) != len(set(flat)):
        dup = sorted({x for x in flat if flat.count(x) > 1})
        err(f"03 section 3: scenarios listed in two tiers: {dup}")
    if set(flat) != scenarios:
        if scenarios - set(flat):
            err(f"03 section 3: no tier assigned to scenarios {sorted(scenarios - set(flat))}")
        if set(flat) - scenarios:
            err(f"03 section 3: mentions scenarios that are not in 01 section 12: {sorted(set(flat) - scenarios)}")
    m = re.search(r"\((\d+) scenarios\)", tier_rows[0])
    if m and int(m.group(1)) != len(tiers[0]):
        err(f"03 section 3: tier 1 says {m.group(1)} scenarios but lists {len(tiers[0])}")
m = re.search(r"(\d+) scenarios fall into three tiers", sec3)
if not m:
    err("03 section 3: the opening lacks 'N scenarios fall into three tiers'")
elif int(m.group(1)) != len(scenarios):
    err(f"03 section 3: says {m.group(1)} scenarios, 01 has {len(scenarios)}")
for v in set(re.findall(r"specification v(\d+\.\d+)", plan)):
    if v != spec_version:
        err(f"03: mentions specification v{v}, but 01 is v{spec_version}")

# ---------- 5. README and Claude Code configuration ----------
m = re.search(r"\[Business specification v(\d+\.\d+)\]", readme)
if not m or m.group(1) != spec_version:
    err(f"README: the document table must say specification v{spec_version}")
m = re.search(r"\[Detailed design, revision (\d+)\]", readme)
if not m or m.group(1) != design_rev:
    err(f"README: the document table must say design revision {design_rev}")

claude_dir = ROOT / ".claude"
config_files = [ROOT / "CLAUDE.md", *sorted(claude_dir.glob("rules/*.md")),
                *sorted(claude_dir.glob("skills/*/SKILL.md")), *sorted(claude_dir.glob("agents/*.md"))]
for cfg in config_files:
    if not cfg.exists():
        continue
    for ref in set(re.findall(r"docs/[\w./-]+\.md", cfg.read_text(encoding="utf-8"))):
        if not (ROOT / ref).exists():
            err(f"{cfg.relative_to(ROOT)}: points to a file that does not exist: {ref}")

# ---------- result ----------
if errors:
    print(f"The document set has {len(errors)} mismatch(es):")
    for e in errors:
        print(" -", e)
    sys.exit(1)

spec_open = len(re.findall(r"^- \[ \]", section(spec, "11."), re.M))
print(f"Documents agree: specification v{spec_version}, design revision {design_rev}, {len(scenarios)} scenarios, "
      f"{len(event_types)} event types; points still open: {spec_open} in 01, {design_open} in 02.")
