from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.db import get_conn, init_tables

router = APIRouter()
init_tables()


class SaveSeqRequest(BaseModel):
    name: str
    sequence: str
    organism: str = "unknown"


class SaveSeqResponse(BaseModel):
    id: int
    name: str
    length: int


@router.post("/sequences/save", response_model=SaveSeqResponse)
def save_sequence(req: SaveSeqRequest) -> SaveSeqResponse:
    seq = req.sequence.replace(" ", "").replace("\n", "").upper()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO user_sequences (name, sequence, organism, length) VALUES (?, ?, ?, ?)",
        (req.name.strip() or "Unnamed", seq, req.organism, len(seq)),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    conn.close()
    return SaveSeqResponse(id=row_id, name=req.name.strip(), length=len(seq))


@router.get("/sequences")
def list_sequences() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, organism, length, created_at FROM user_sequences ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/sequences/{seq_id}")
def get_sequence(seq_id: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT id, name, organism, sequence, length, created_at FROM user_sequences WHERE id = ?",
        (seq_id,),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return dict(row)


@router.delete("/sequences/{seq_id}")
def delete_sequence(seq_id: int) -> dict:
    conn = get_conn()
    affected = conn.execute(
        "DELETE FROM user_sequences WHERE id = ?", (seq_id,)
    ).rowcount
    conn.commit()
    conn.close()
    if affected == 0:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return {"deleted": seq_id}
