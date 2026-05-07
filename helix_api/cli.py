from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("HELIX_API_HOST", "127.0.0.1")
    port = int(os.getenv("HELIX_API_PORT", "8000"))
    uvicorn.run("helix_api.main:app", host=host, port=port, reload=False)
