"""Start one service in Docker Compose: apply its migrations, then serve its HTTP API.

Every service container runs the same image and command (``python -m common.service``);
the environment says which service it is:

- ``SERVICE``: ``branch``, ``inventory``, ``kitchen`` or ``query``
- ``DATABASE_URL``: the service's own database
- ``BRANCH_ID``: for ``branch`` only (``POS01``, ``POS02``, ``ONLINE``)
- ``RELOAD``: ``1`` to restart on source changes (the default in compose)

The layout and the networks are in section 2 of docs/03-implementation-plan.md.
"""

import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg
import uvicorn

from common.migrate import apply_migrations

BACKEND = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ServiceSpec:
    module_dir: str
    app: str


SERVICES: dict[str, ServiceSpec] = {
    "branch": ServiceSpec("order-service", "order_service.app:app"),
    "inventory": ServiceSpec("inventory-service", "inventory_service.app:app"),
    "kitchen": ServiceSpec("kitchen-service", "kitchen_service.app:app"),
    "query": ServiceSpec("query-service", "query_service.app:app"),
}


def identity() -> dict[str, str]:
    """Which service and which instance answered; shown by every /health."""
    info = {
        "service": os.environ.get("SERVICE", "unknown"),
        "instance": socket.gethostname(),
    }
    branch = os.environ.get("BRANCH_ID")
    if branch:
        info["branch"] = branch
    return info


def main() -> int:
    name = os.environ.get("SERVICE", "")
    spec = SERVICES.get(name)
    if spec is None:
        print(f"SERVICE must be one of {', '.join(SERVICES)}, got {name!r}", file=sys.stderr)
        return 2
    dsn = os.environ["DATABASE_URL"]
    with psycopg.connect(dsn) as conn:
        applied = apply_migrations(conn, BACKEND / spec.module_dir / "migrations")
    print(f"{name}: migrations applied: {', '.join(applied) or 'none new'}", flush=True)

    reload = os.environ.get("RELOAD", "0") == "1"
    uvicorn.run(
        spec.app,
        host="0.0.0.0",
        port=8000,
        reload=reload,
        reload_dirs=[str(BACKEND / "common" / "src"), str(BACKEND / spec.module_dir / "src")]
        if reload
        else None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
