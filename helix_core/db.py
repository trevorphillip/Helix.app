"""SQLite helpers used by both desktop and mobile builds."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

_DB_PATH = Path("helix.db")


def _connect(db_file: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: Optional[Path] = None) -> sqlite3.Connection:
    """Initialise the lightweight SQLite database used for caching.

    The schema is intentionally tiny; we only create the ``sessions`` table that
    the legacy desktop build expected.  Additional tables can be added by the
    caller if needed.
    """

    db_file = Path(path) if path else _DB_PATH
    conn = _connect(db_file)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            username TEXT NOT NULL DEFAULT 'anonymous',
            session_name TEXT NOT NULL DEFAULT 'Session',
            mode TEXT NOT NULL DEFAULT 'sandbox',
            payload TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def save_session(
    payload: dict[str, Any],
    *,
    username: str,
    session_name: str,
    mode: str = "sandbox",
    path: Optional[Path] = None,
) -> int:
    conn = init_db(path)
    cur = conn.execute(
        """
        INSERT INTO sessions (username, session_name, mode, payload)
        VALUES (?, ?, ?, ?)
        """,
        (username, session_name, mode, json.dumps(payload)),
    )
    conn.commit()
    session_id = int(cur.lastrowid)
    conn.close()
    return session_id


def list_sessions(
    *,
    username: Optional[str] = None,
    mode: Optional[str] = None,
    limit: int = 25,
    path: Optional[Path] = None,
) -> list[dict[str, Any]]:
    conn = init_db(path)
    clauses: list[str] = []
    params: list[Any] = []
    if username:
        clauses.append("username = ?")
        params.append(username)
    if mode:
        clauses.append("mode = ?")
        params.append(mode)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT id, created_at, username, session_name, mode
        FROM sessions
        {where}
        ORDER BY id DESC
        LIMIT ?
    """
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def load_session(session_id: int, path: Optional[Path] = None) -> dict[str, Any]:
    conn = init_db(path)
    row = conn.execute(
        """
        SELECT id, created_at, username, session_name, mode, payload
        FROM sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()
    conn.close()
    if row is None:
        raise KeyError(f"Session {session_id} was not found")
    data = dict(row)
    data["payload"] = json.loads(data["payload"])
    return data
