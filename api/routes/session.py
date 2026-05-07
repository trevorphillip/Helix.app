from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from helix_core.db import list_sessions, save_session, load_session

router = APIRouter()


class SaveSessionRequest(BaseModel):
    username: str
    name: str
    payload: dict[str, Any]


class SaveSessionResponse(BaseModel):
    id: int


@router.get("/sessions")
def get_sessions(username: Optional[str] = Query(default=None)) -> list[dict]:
    return list_sessions(username=username or None, mode="sandbox", limit=10)


@router.post("/sessions/save", response_model=SaveSessionResponse)
def save_session_route(req: SaveSessionRequest) -> SaveSessionResponse:
    session_id = save_session(
        req.payload,
        username=req.username or "anonymous",
        session_name=req.name.strip() or "API session",
        mode="sandbox",
    )
    return SaveSessionResponse(id=session_id)


@router.get("/sessions/{session_id}")
def get_session(session_id: int) -> dict:
    session = load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session
