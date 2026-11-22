"""Write the performance part of the course report from the files bin/perf leaves in
/perf/results (the repository's perf/results/):

- ``statistics.json``: JMeter's aggregate per API (its HTML dashboard's data);
- ``stats.csv``: ``docker stats`` every few seconds while the load ran, as
  ``<unix time>;<container>;<CPU %>;<memory used> / <limit>``;
- ``latency.json``: the time from creating an order to Reserved (scripts/perf_latency.py);
- ``run.txt``: when the run took place and with which JMeter properties.

    docker compose exec -T tools python scripts/report_perf.py > report/generated/hieu-nang.md
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

RESULTS = Path("/perf/results")
ORDER = [
    "POST /orders",
    "GET /dishes",
    "GET /orders",
    "GET /tickets",
    "GET /stock",
    "GET /reports/summary",
]
UNITS = {"B": 1 / 2**20, "KiB": 1 / 2**10, "MiB": 1, "GiB": 2**10, "kB": 1e3 / 2**20,
         "MB": 1e6 / 2**20, "GB": 1e9 / 2**20}  # fmt: skip


def ms(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def number(value: float, decimals: int = 1) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def mib(text: str) -> float:
    m = re.match(r"([\d.]+)\s*([A-Za-z]+)", text.strip())
    if not m:
        return 0.0
    return float(m.group(1)) * UNITS.get(m.group(2), 1)


def load_table(stats: dict[str, Any]) -> list[str]:
    rows = [
        "| Chức năng (API) | Số yêu cầu | Lỗi | Trung bình (ms) | Nhỏ nhất (ms) | Trung vị (ms) "
        "| 95% (ms) | Lớn nhất (ms) | Thông lượng (yêu cầu/giây) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    labels = [label for label in ORDER if label in stats] + ["Total"]
    for label in labels:
        s = stats[label]
        name = "**Tổng**" if label == "Total" else f"`{label}`"
        rows.append(
            f"| {name} | {s['sampleCount']} | {s['errorCount']} ({number(s['errorPct'], 2)} %) "
            f"| {ms(s['meanResTime'])} | {ms(s['minResTime'])} | {ms(s['medianResTime'])} "
            f"| {ms(s['pct2ResTime'])} | {ms(s['maxResTime'])} | {number(s['throughput'])} |"
        )
    return rows


def resource_table(lines: list[str]) -> list[str]:
    cpu: dict[str, float] = defaultdict(float)
    mem: dict[str, float] = defaultdict(float)
    total_by_time: dict[str, float] = defaultdict(float)
    for line in lines:
        parts = line.split(";")
        if len(parts) != 4:
            continue
        at, name, cpu_text, mem_text = parts
        name = re.sub(r"^order-system-|-1$", "", name)
        if name.startswith("jmeter-run-"):
            name = "jmeter (bộ tạo tải)"
        used = mib(mem_text.split("/")[0])
        cpu[name] = max(cpu[name], float(cpu_text.rstrip("%") or 0))
        mem[name] = max(mem[name], used)
        total_by_time[at] += used
    rows = [
        "| Container | CPU cao nhất (%) | Bộ nhớ cao nhất (MiB) |",
        "|---|---|---|",
    ]
    for name in sorted(cpu, key=lambda n: -cpu[n]):
        rows.append(f"| `{name}` | {number(cpu[name])} | {number(mem[name], 0)} |")
    if total_by_time:
        peak = max(total_by_time.values())
        rows.append(f"| **Cả cụm** (tổng bộ nhớ tại một thời điểm) | | {number(peak, 0)} |")
    return rows


def main() -> None:
    stats = json.loads((RESULTS / "statistics.json").read_text())
    run = (RESULTS / "run.txt").read_text().strip()
    out = [
        "<!-- Sinh tự động bởi backend/scripts/report_perf.py từ perf/results/ (bin/perf). "
        "Không sửa tay. -->",
        "",
        f"Lần chạy: {run}.",
        "",
        "##### Thời gian đáp ứng theo chức năng",
        "",
        *load_table(stats),
        "",
        "Một yêu cầu bị tính là lỗi khi dịch vụ trả mã HTTP 4xx, 5xx hoặc không trả lời trong "
        "60 giây. Cột 95 % là thời gian mà 95 % số yêu cầu không vượt quá.",
    ]
    latency_file = RESULTS / "latency.json"
    if latency_file.exists():
        latency = json.loads(latency_file.read_text())
        r = latency["reserved_ms"]
        statuses = ", ".join(f"`{k}` {v}" for k, v in sorted(latency["by_status"].items()))
        out += [
            "",
            "##### Thời gian từ lúc tạo đơn tới khi chi nhánh thấy Đã giữ",
            "",
            f"{latency['orders']} đơn tạo lần lượt ở POS01 sau khi chạy tải ({statuses}); mỗi đơn "
            f"được hỏi lại mỗi {latency['poll_ms']:.0f} ms. Đơn đi trọn đường: hàng chờ gửi, "
            "Kafka, Kho, rồi `status-events.POS01` về chi nhánh.",
            "",
            "| Nhỏ nhất (ms) | Trung bình (ms) | Trung vị (ms) | 95% (ms) | Lớn nhất (ms) |",
            "|---|---|---|---|---|",
            f"| {ms(r['min'])} | {ms(r['mean'])} | {ms(r['median'])} | {ms(r['p95'])} "
            f"| {ms(r['max'])} |"
            if r
            else "| - | - | - | - | - |",
        ]
    stats_file = RESULTS / "stats.csv"
    if stats_file.exists():
        out += [
            "",
            "##### Tài nguyên trong lúc chạy tải",
            "",
            "Giá trị cao nhất mà `docker stats` ghi được trong lúc chạy tải. CPU 100 % là trọn "
            "một nhân.",
            "",
            *resource_table(stats_file.read_text().splitlines()),
        ]
    print("\n".join(out))


if __name__ == "__main__":
    main()
