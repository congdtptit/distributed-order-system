"""Write the test part of the course report: the 44 scenarios with their tier and result.

Inputs:
- a JUnit XML file from a full pytest run; each test carries its ``kb(<n>)`` numbers as
  properties (the ``_scenario_number`` fixture of backend/conftest.py);
- the scenario table in Vietnamese, from the frozen original of specification v1.5
  (docs/archive/vi-2026-11-21/01-dac-ta-nghiep-vu.md, section 12; the scenarios have not changed
  since: section 12 of docs/01-business-spec.md is the master);
- the tiers, from section 3 of docs/03-implementation-plan.md.

    docker compose exec -T tools pytest -p no:cacheprovider --junitxml=/tmp/junit.xml
    docker compose exec -T tools python scripts/report_tests.py /tmp/junit.xml \\
        > report/generated/kiem-thu.md          # or write to /report/generated inside tools

Scenarios with parts left to later steps are named in PARTIAL; a scenario counts as "Đạt" only
when it has tests and all of them pass.
"""

import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

DOCS = Path("/docs")
SCENARIOS_VI = DOCS / "archive" / "vi-2026-11-21" / "01-dac-ta-nghiep-vu.md"
PLAN = DOCS / "03-implementation-plan.md"

TIER_NAMES = {"1": "Tầng 1", "2": "Tầng 2", "3": "Tầng 3"}
PARTIAL: dict[int, str] = {
    6: "Phần đợt 1 đạt; phần món chuyển sang Hết thuộc đợt 2",
    48: "Phần đợt 1 đạt; phần món trở lại Còn thuộc đợt 2",
    24: "Kiểm tới topic; chi nhánh áp dụng tin ở bước 6",
    4: "Kiểm tới topic; chi nhánh hiển thị ở bước 6",
    3: "Bếp và Kho kiểm đủ; chi nhánh áp dụng tin ở bước 6",
    8: "Kiểm tới topic; chi nhánh tắt cờ hủy ở bước 6",
    23: "Kiểm tới topic; chi nhánh hiển thị ở bước 6",
    33: "Kiểm tới topic; chi nhánh hiển thị ở bước 6",
}


def scenarios() -> list[tuple[int, str, str, str]]:
    """(number, scenario, expected result, rule) in Vietnamese."""
    rows: list[tuple[int, str, str, str]] = []
    for line in SCENARIOS_VI.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| (\d+) \| (.+?) \| (.+?) \| (.+?) \|$", line)
        if m and int(m.group(1)) <= 55 and not line.startswith("| 1 | Dùng chung"):
            rows.append((int(m.group(1)), m.group(2), m.group(3), m.group(4)))
    seen: dict[int, tuple[int, str, str, str]] = {}
    for row in rows:  # the scenario table is the last table with these numbers
        seen[row[0]] = row
    return [seen[n] for n in sorted(seen)]


def tiers() -> dict[int, str]:
    """Scenario number -> tier, from the tier table in section 3 of the plan."""
    found: dict[int, str] = {}
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        m = re.match(
            r"^\| ([123])\. [^|]+\| [^|]+\| ([\d,\s\u2013-]+?)(?: \(\d+ scenarios\))? \|$", line
        )
        if not m:
            continue
        for part in m.group(2).split(","):
            part = part.strip()
            if not part:
                continue
            bounds = re.split("[\u2013-]", part)
            first, last = int(bounds[0]), int(bounds[-1])
            for n in range(first, last + 1):
                found[n] = TIER_NAMES[m.group(1)]
    return found


def results(junit: Path) -> dict[int, list[bool]]:
    """Scenario number -> one entry per test: True if it passed."""
    by_scenario: dict[int, list[bool]] = defaultdict(list)
    for case in ET.parse(junit).getroot().iter("testcase"):
        numbers = [int(p.get("value", "0")) for p in case.iter("property") if p.get("name") == "kb"]
        failed = any(case.find(tag) is not None for tag in ("failure", "error", "skipped"))
        for n in numbers:
            by_scenario[n].append(not failed)
    return by_scenario


def cell(text: str) -> str:
    return text.replace("|", "\\|")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    junit = Path(sys.argv[1])
    tier = tiers()
    ran = results(junit)
    rows = scenarios()
    lines = [
        "<!-- Sinh tự động bởi backend/scripts/report_tests.py từ một lần chạy pytest đầy đủ."
        " Không sửa tay. -->",
        "",
        "| STT | Kịch bản | Kết quả mong đợi | Quy tắc | Tầng | Số test | Kết quả |",
        "|---|---|---|---|---|---|---|",
    ]
    passed = failed = untested = 0
    for number, scenario, expected, rule in rows:
        outcomes = ran.get(number, [])
        if not outcomes:
            state = "Chưa kiểm thử"
            untested += 1
        elif all(outcomes):
            state = "Đạt"
            passed += 1
        else:
            state = f"Lỗi ({outcomes.count(False)}/{len(outcomes)} test)"
            failed += 1
        if number in PARTIAL and outcomes:
            state += f" ({PARTIAL[number]})"
        lines.append(
            f"| {number} | {cell(scenario)} | {cell(expected)} | {cell(rule)} | "
            f"{tier.get(number, '')} | {len(outcomes) or ''} | {state} |"
        )
    total_tests = len(list(ET.parse(junit).getroot().iter("testcase")))
    total_failed = sum(
        1
        for case in ET.parse(junit).getroot().iter("testcase")
        if any(case.find(tag) is not None for tag in ("failure", "error"))
    )
    lines += [
        "",
        "| Tổng hợp kết quả kiểm thử | Số lượng |",
        "|---|---|",
        f"| Kịch bản đạt | {passed} |",
        f"| Kịch bản lỗi | {failed} |",
        f"| Kịch bản chưa kiểm thử (thuộc các bước sau) | {untested} |",
        f"| Tổng số kịch bản | {len(rows)} |",
        f"| Tổng số test tự động đã chạy (kể cả test không gắn kịch bản) | {total_tests} |",
        f"| Trong đó test lỗi | {total_failed} |",
    ]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
