"""Management's summary report (section 8 of docs/01-business-spec.md), read from the Central
Order Replica only (section 5 of docs/02-detailed-design.md).

For each branch: its "data as of" time, the number of orders in each status, and the number of
Cancelled and Failed orders by reason. Only the branches' order statuses count; a cancel
request still pending at the Kitchen changes no status and so no figure.

"Data as of" is the branch's ``replication_heartbeat.beat_at`` as it has reached the central
DB. Logical replication applies one branch's transactions in commit order, so every order
change that branch committed before that time is in the figures. The counts and the heartbeat
are read in one repeatable-read snapshot, so a heartbeat that arrives between two reads cannot
claim figures newer than the ones shown. The age is measured against the central DB's clock;
in this project every database runs on the same machine, so the two clocks agree.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

import psycopg

STATUSES: Final = ("CHO_KHO", "DA_GIU", "HOAN_TAT", "DA_HUY", "THAT_BAI")
CLOSED_WITH_REASON: Final = ("DA_HUY", "THAT_BAI")


@dataclass
class ReasonCount:
    status: str
    reason_code: str | None
    count: int


@dataclass
class BranchSummary:
    branch_id: str
    data_as_of: datetime | None = None
    data_age_s: float | None = None
    total: int = 0
    by_status: dict[str, int] = field(default_factory=lambda: dict.fromkeys(STATUSES, 0))
    reasons: list[ReasonCount] = field(default_factory=list[ReasonCount])


@dataclass
class Summary:
    generated_at: datetime
    branches: list[BranchSummary]


def summary(conn: psycopg.Connection[Any], branches: list[str]) -> Summary:
    """``branches`` are the configured ones, listed first and in that order, with or without
    data; a branch that appears only in the data follows, sorted by id."""
    conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    now_row = conn.execute("SELECT now()").fetchone()
    assert now_row is not None
    generated_at: datetime = now_row[0]
    lines: dict[str, BranchSummary] = {b: BranchSummary(b) for b in branches}

    def line(branch_id: str) -> BranchSummary:
        return lines.setdefault(branch_id, BranchSummary(branch_id))

    beats = conn.execute(
        "SELECT branch_id, beat_at, extract(epoch FROM now() - beat_at)::float8 "
        "FROM replication_heartbeat ORDER BY branch_id"
    ).fetchall()
    for branch_id, beat_at, age_s in beats:
        target = line(branch_id)
        target.data_as_of = beat_at
        target.data_age_s = age_s
    counts = conn.execute(
        "SELECT branch_id, status, close_reason, count(*)::int FROM orders "
        "GROUP BY branch_id, status, close_reason "
        "ORDER BY branch_id, status, close_reason NULLS LAST"
    ).fetchall()
    for branch_id, status, reason, count in counts:
        target = line(branch_id)
        target.by_status[status] += count
        target.total += count
        if status in CLOSED_WITH_REASON:
            target.reasons.append(ReasonCount(status, reason, count))
    conn.rollback()  # read only: end the snapshot

    extra = sorted(set(lines) - set(branches))
    ordered = [lines[b] for b in branches] + [lines[b] for b in extra]
    for target in ordered:
        target.reasons.sort(key=lambda r: (STATUSES.index(r.status), r.reason_code or ""))
    return Summary(generated_at, ordered)
