"""HTTP entry point of the Order Query service. The APIs are in section 6 of docs/02-detailed-
design.md.
"""

from fastapi import FastAPI

app = FastAPI(title="Order Query")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
