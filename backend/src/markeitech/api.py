from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI

app = FastAPI(
    title="Markeitech API",
    version="0.1.0",
    summary="Stage 0 API shell for Markeitech.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readiness")
def readiness() -> dict[str, Any]:
    return {
        "ready": True,
        "stage": "0",
        "mode": os.getenv("MARKEITECH_MODE", "data_only"),
        "execution_enabled": os.getenv("MARKEITECH_ENABLE_EXECUTION", "false").lower() == "true",
    }


def main() -> None:
    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("markeitech.api:app", host=host, port=port, reload=True)
