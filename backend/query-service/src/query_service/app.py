"""HTTP entry point of the Order Query service: Management's report, read from the Central
Order Replica only, never from a branch DB.

The APIs are in section 6 of docs/02-detailed-design.md. ``BRANCHES`` lists the branches the
report always shows (default ``POS01,POS02,ONLINE``, as for the topics).
"""

import os
from datetime import datetime
from typing import Annotated, Any

import psycopg
from fastapi import Depends, FastAPI
from pydantic import BaseModel

from common.api import get_conn
from common.service import identity
from query_service.report import summary

app = FastAPI(title="Order Query")


def get_branches() -> list[str]:
    return [b for b in os.environ.get("BRANCHES", "POS01,POS02,ONLINE").split(",") if b]


Conn = Annotated[psycopg.Connection[Any], Depends(get_conn)]
Branches = Annotated[list[str], Depends(get_branches)]


class StatusCounts(BaseModel):
    CHO_KHO: int
    DA_GIU: int
    HOAN_TAT: int
    DA_HUY: int
    THAT_BAI: int


class ReasonCount(BaseModel):
    status: str
    """DA_HUY or THAT_BAI."""
    reason_code: str | None
    count: int


class BranchSummary(BaseModel):
    branch_id: str
    data_as_of: datetime | None
    """The branch's latest heartbeat that has reached the central DB; every order change the
    branch committed before it is counted. Null until the first one arrives."""
    data_age_s: float | None
    """How long before ``generated_at`` that was."""
    total: int
    by_status: StatusCounts
    reasons: list[ReasonCount]
    """Cancelled and Failed orders by reason; cancel reasons include the Kitchen's."""


class Summary(BaseModel):
    generated_at: datetime
    branches: list[BranchSummary]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", **identity()}


@app.get("/reports/summary")
def get_summary(conn: Conn, branches: Branches) -> Summary:
    report = summary(conn, branches)
    return Summary.model_validate(report, from_attributes=True)
