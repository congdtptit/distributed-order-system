"""HTTP entry point of the Kitchen service.

The APIs are in section 6 of docs/02-detailed-design.md.
"""

from fastapi import FastAPI

from common.service import identity

app = FastAPI(title="Kitchen")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", **identity()}
