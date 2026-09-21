"""SQLite store for OCR'd screen text. Local disk only."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home() / ".dayglass"
DB_PATH = HOME / "dayglass.sqlite"


def connect() -> sqlite3.Connection:
    HOME.mkdir(parents=True, mode=0o700, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS frames (
            id INTEGER PRIMARY KEY,
            captured_at TEXT NOT NULL,
            text TEXT NOT NULL,
            image_path TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS frames_fts USING fts5(
            text,
            content='frames',
            content_rowid='id'
        )
        """
    )
    conn.commit()
    return conn


def insert_frame(conn: sqlite3.Connection, text: str, image_path: str | None) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.execute(
        "INSERT INTO frames (captured_at, text, image_path) VALUES (?, ?, ?)",
        (now, text, image_path),
    )
    rowid = int(cur.lastrowid)
    conn.execute(
        "INSERT INTO frames_fts (rowid, text) VALUES (?, ?)",
        (rowid, text),
    )
    conn.commit()
    return rowid


def search(conn: sqlite3.Connection, query: str, limit: int = 8) -> list[sqlite3.Row]:
    # FTS5 query: wrap as a phrase-ish prefix match; fall back to LIKE.
    try:
        return list(
            conn.execute(
                """
                SELECT f.id, f.captured_at, snippet(frames_fts, 0, '', '', ' … ', 24) AS snip
                FROM frames_fts
                JOIN frames f ON f.id = frames_fts.rowid
                WHERE frames_fts MATCH ?
                ORDER BY f.id DESC
                LIMIT ?
                """,
                (query, limit),
            )
        )
    except sqlite3.OperationalError:
        like = f"%{query}%"
        return list(
            conn.execute(
                """
                SELECT id, captured_at, substr(text, 1, 240) AS snip
                FROM frames
                WHERE text LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (like, limit),
            )
        )


def recent_text(conn: sqlite3.Connection, limit: int = 12) -> str:
    rows = conn.execute(
        "SELECT captured_at, text FROM frames ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    chunks = []
    for row in rows:
        body = (row["text"] or "").strip()
        if not body:
            continue
        chunks.append(f"[{row['captured_at']}]\n{body[:4000]}")
    return "\n\n".join(reversed(chunks))


def today_text(conn: sqlite3.Connection) -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = conn.execute(
        """
        SELECT captured_at, text FROM frames
        WHERE captured_at LIKE ?
        ORDER BY id ASC
        """,
        (day + "%",),
    )
    parts = []
    for row in rows:
        body = (row["text"] or "").strip()
        if body:
            parts.append(f"[{row['captured_at']}]\n{body[:2500]}")
    return "\n\n".join(parts)
