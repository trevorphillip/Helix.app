from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import grnas, session, scoring, ai, orfs, variants, protein, pdb, offtarget, primers, genes, sequences, outcome, export, base_editor

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
app.include_router(outcome.router,   prefix="/api")
app.include_router(export.router,    prefix="/api")
app.include_router(base_editor.router, prefix="/api/baseedit")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.4.0"}


# Find frontend dist directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

print(f"Looking for frontend at: {FRONTEND_DIST}")
print(f"Frontend exists: {os.path.exists(FRONTEND_DIST)}")

# Mount assets folder
assets_dir = os.path.join(FRONTEND_DIST, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
async def serve_root():
    index = os.path.join(FRONTEND_DIST, "index.html")
    return FileResponse(index)


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        return {"error": "not found"}
    index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"error": "Frontend not built", "looked_at": FRONTEND_DIST, "base_dir": BASE_DIR}