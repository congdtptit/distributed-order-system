"""HTTP entry point of the Branch service.

The APIs are in section 6 of docs/02-detailed-design.md.
"""

from fastapi import FastAPI

app = FastAPI(title="Branch")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
