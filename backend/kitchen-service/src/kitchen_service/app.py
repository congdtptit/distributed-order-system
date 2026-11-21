"""HTTP entry point of the Kitchen service. The APIs are in section 6 of docs/02-detailed-
design.md.
"""

from fastapi import FastAPI

app = FastAPI(title="Kitchen")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
