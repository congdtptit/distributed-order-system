"""Write the database part of the course report from the live schemas.

For each kind of database (Inventory, Kitchen, branch, Central Order Replica) it prints, in
Markdown: an introduction linking to its ER PNG diagram and one table per DB table in
the template's columns Field, Type, Null, Key, Default, Extra (section 1 of
docs/04-course-report.md). Reading the running databases keeps the report in line with the
migrations. Table and column names stay as they are in the schema; the prose is Vietnamese
because the report is.

    docker compose exec -T tools python scripts/report_schema.py > ../report/generated/csdl.md

(run from backend/ on the host, or redirect wherever the report lives).
"""

import re
import sys
from collections import defaultdict
from typing import Any

import psycopg

DATABASES: list[tuple[str, str, str, str, str, str, str]] = [
    (
        "4.2.2.1. Inventory DB",
        "Inventory DB",
        "postgresql://app:app@inventory-db:5432/inventory",
        "inventory-db",
        "images/er-inventory-db.png",
        "Hình 2.20",
        "Sơ đồ thực thể - quan hệ của cơ sở dữ liệu Inventory DB",
    ),
    (
        "4.2.2.2. Kitchen DB",
        "Kitchen DB",
        "postgresql://app:app@kitchen-db:5432/kitchen",
        "kitchen-db",
        "images/er-kitchen-db.png",
        "Hình 2.21",
        "Sơ đồ thực thể - quan hệ của cơ sở dữ liệu Kitchen DB",
    ),
    (
        "4.2.2.3. Branch DB (POS01, POS02, ONLINE)",
        "Branch DB (POS01, POS02, ONLINE)",
        "postgresql://app:app@pos01-db:5432/branch",
        "pos01-db",
        "images/er-branch-db.png",
        "Hình 2.22",
        "Sơ đồ thực thể - quan hệ của cơ sở dữ liệu Branch DB",
    ),
    (
        "4.2.2.4. Central Order Replica",
        "Central Order Replica",
        "postgresql://app:app@central-db:5432/central",
        "central-db",
        "images/er-central-db.png",
        "Hình 2.23",
        "Sơ đồ thực thể - quan hệ của cơ sở dữ liệu Central Order Replica",
    ),
]
SKIP = {"schema_migrations"}  # the migration runner's ledger, not part of the design

COLUMNS = """
SELECT c.table_name, c.column_name, c.data_type, c.udt_name, c.is_nullable,
       c.column_default, c.character_maximum_length, c.numeric_precision, c.numeric_scale
  FROM information_schema.columns c
  JOIN information_schema.tables t
    ON t.table_schema = c.table_schema AND t.table_name = c.table_name
 WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'
 ORDER BY c.table_name, c.ordinal_position
"""

# Every constraint with its columns: p = primary key, u = unique, f = foreign key, c = check.
CONSTRAINTS = """
SELECT rel.relname, con.contype, con.conname,
       ARRAY(SELECT a.attname FROM unnest(con.conkey) k
               JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k) AS cols,
       ref.relname AS ref_table,
       ARRAY(SELECT a.attname FROM unnest(con.confkey) k
               JOIN pg_attribute a ON a.attrelid = con.confrelid AND a.attnum = k) AS ref_cols,
       pg_get_constraintdef(con.oid) AS definition
  FROM pg_constraint con
  JOIN pg_class rel ON rel.oid = con.conrelid
  JOIN pg_namespace n ON n.oid = rel.relnamespace
  LEFT JOIN pg_class ref ON ref.oid = con.confrelid
 WHERE n.nspname = 'public'
 ORDER BY rel.relname, con.conname
"""


def type_name(row: tuple[Any, ...]) -> str:
    _t, _c, data_type, udt, _n, _d, length, precision, scale = row
    if data_type == "numeric" and precision is not None:
        return f"NUMERIC({precision},{scale})"
    if data_type == "ARRAY":
        return f"{str(udt).lstrip('_').upper()}[]"
    if data_type == "character varying" and length:
        return f"VARCHAR({length})"
    names = {
        "timestamp with time zone": "TIMESTAMPTZ",
        "integer": "INT",
        "bigint": "BIGINT",
        "boolean": "BOOLEAN",
        "text": "TEXT",
        "uuid": "UUID",
        "jsonb": "JSONB",
    }
    return names.get(str(data_type), str(data_type).upper())


def describe(
    conn: psycopg.Connection[Any],
) -> tuple[dict[str, list[tuple[Any, ...]]], list[tuple[Any, ...]]]:
    columns: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    for row in conn.execute(COLUMNS).fetchall():
        if row[0] not in SKIP:
            columns[str(row[0])].append(row)
    constraints = [r for r in conn.execute(CONSTRAINTS).fetchall() if r[0] not in SKIP]
    return columns, constraints


def _key_order(key: str) -> tuple[int, str]:
    return ({"PRI": 0, "UNI": 1}.get(key, 2), key)


def cell(value: object) -> str:
    return "" if value is None else str(value).replace("|", "\\|").replace("\n", " ")


def format_default(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    text = re.sub(r"::(?:text\[\]|text|jsonb|numeric)", "", text)
    return text


def format_check(expr: str) -> str:
    m = re.match(r"^CHECK \(\((.+?) = ANY \(ARRAY\[(.+?)\]\)\)\)$", expr)
    if m:
        col = m.group(1)
        items = re.sub(r"::text", "", m.group(2))
        return f"CHECK ({col} IN ({items}))"
    cleaned = re.sub(r"::(?:text|numeric)", "", expr)
    cleaned = re.sub(r"\(\((\w+)\s*([><=]+)\s*\(?(-?\d+)\)?\)\)", r"(\1 \2 \3)", cleaned)
    return cleaned


def render(
    heading: str,
    title: str,
    host: str,
    er_img: str,
    fig_label: str,
    fig_caption: str,
    table_num: int,
    conn: psycopg.Connection[Any],
) -> tuple[str, int]:
    columns, constraints = describe(conn)
    keys: dict[tuple[str, str], list[str]] = defaultdict(list)
    checks: dict[tuple[str, str], list[str]] = defaultdict(list)
    for table, kind, _name, cols, ref_table, ref_cols, definition in constraints:
        cols = list(cols)
        if kind == "p":
            for c in cols:
                keys[(table, c)].append("PRI")
        elif kind == "u":
            uni_label = "UNI (tổ hợp)" if len(cols) > 1 else "UNI"
            for c in cols:
                keys[(table, c)].append(uni_label)
        elif kind == "f":
            for c, rc in zip(cols, ref_cols, strict=True):
                keys[(table, c)].append(f"FK → {ref_table}.{rc}")
        elif kind == "c" and len(cols) == 1:
            checks[(table, cols[0])].append(format_check(str(definition)))

    end_table = table_num + len(columns) - 1
    range_text = (
        f"Bảng 2.{table_num}"
        if table_num == end_table
        else f"từ Bảng 2.{table_num} đến Bảng 2.{end_table}"
    )
    out = [
        f"##### {heading}",
        "",
        f"Lược đồ thực thể và các ràng buộc bảng của `{host}` thể hiện trên {fig_label}; "
        f"chi tiết cấu trúc {len(columns)} bảng dữ liệu được trình bày {range_text}.",
        "",
        f"![{fig_label}. {fig_caption}]({er_img})",
        "",
    ]

    for table, rows in columns.items():
        caption = f"*Bảng 2.{table_num}. Cấu trúc bảng `{table}` ({title})*"
        table_num += 1
        out += [
            "| Field | Type | Null | Key | Default | Extra |",
            "|---|---|---|---|---|---|",
        ]
        for r in rows:
            name = str(r[1])
            default = format_default(r[5])
            extra: list[str] = []
            if isinstance(default, str) and default.startswith("nextval("):
                default, extra = None, ["auto_increment"]
            extra += checks[(table, name)]
            out.append(
                "| "
                + " | ".join(
                    cell(v)
                    for v in (
                        name,
                        type_name(r),
                        "YES" if r[4] == "YES" else "NO",
                        ", ".join(sorted(keys[(table, name)], key=_key_order)),
                        default,
                        "; ".join(extra),
                    )
                )
                + " |"
            )
        out += ["", caption, ""]
    return "\n".join(out), table_num


def main() -> int:
    parts = [
        "<!-- Sinh tự động bởi backend/scripts/report_schema.py từ các CSDL đang chạy."
        " Không sửa tay: chạy lại script sau mỗi migration. -->",
        "",
    ]
    table_num = 6
    for heading, title, dsn, host, er_img, fig_label, fig_caption in DATABASES:
        try:
            with psycopg.connect(dsn, connect_timeout=5) as conn:
                block, table_num = render(
                    heading, title, host, er_img, fig_label, fig_caption, table_num, conn
                )
                parts.append(block)
        except psycopg.OperationalError as exc:
            print(f"{host}: not reachable ({exc}); start the cluster first", file=sys.stderr)
            return 1
    print("\n".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
