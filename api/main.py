from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import grnas, session, scoring, ai, orfs, variants, protein, pdb, offtarget, primers, genes, sequences

app = FastAPI(title="Helix API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(grnas.router, prefix="/api")
app.include_router(session.router, prefix="/api")
app.include_router(scoring.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(orfs.router, prefix="/api")
app.include_router(variants.router, prefix="/api")
app.include_router(protein.router, prefix="/api")
app.include_router(pdb.router, prefix="/api")
app.include_router(offtarget.router, prefix="/api")
app.include_router(primers.router, prefix="/api")
app.include_router(genes.router, prefix="/api")
app.include_router(sequences.router, prefix="/api")


@app.get("/")
def health() -> dict:
    return {"status": "ok", "version": "0.4.0"}


# Serve React frontend in production
frontend_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(
        directory=os.path.join(frontend_dist, 'assets')
    ), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        index = os.path.join(frontend_dist, 'index.html')
        return FileResponse(index)
