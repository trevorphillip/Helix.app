"""Shared SQLite helpers for API-layer caching and user data tables."""
from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_PATH = Path("helix.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_tables() -> None:
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS gene_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            query       TEXT    NOT NULL,
            organism    TEXT    NOT NULL,
            results_json TEXT   NOT NULL,
            fetched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sequence_cache (
            accession   TEXT PRIMARY KEY,
            name        TEXT,
            organism    TEXT,
            sequence    TEXT NOT NULL,
            length      INTEGER,
            fetched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_sequences (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            sequence    TEXT NOT NULL,
            organism    TEXT DEFAULT 'unknown',
            length      INTEGER,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
