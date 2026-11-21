"""Write each service's OpenAPI document to frontend/src/api/openapi/<service>.json.

The screens' TypeScript types are generated from these files (section 6 of
docs/02-detailed-design.md). Run after changing an API:

    docker compose exec tools python scripts/dump_openapi.py
    docker compose exec frontend npm run gen:api
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI

from inventory_service.app import app as inventory
from kitchen_service.app import app as kitchen
from order_service.app import app as branch
from query_service.app import app as reports

# In compose the tools container mounts frontend/src/api/openapi at OPENAPI_DIR; in a full
# checkout (CI) the default path is used.
OUT = Path(
    os.environ.get(
        "OPENAPI_DIR",
        Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "openapi",
    )
)

APPS: dict[str, FastAPI] = {
    "branch": branch,
    "inventory": inventory,
    "kitchen": kitchen,
    "reports": reports,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, app in APPS.items():
        path = OUT / f"{name}.json"
        path.write_text(
            json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {name}.json")


if __name__ == "__main__":
    main()
