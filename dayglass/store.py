"""SQLite store for OCR'd screen text. Local disk only."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home() / ".dayglass"
DB_PATH = HOME / "dayglass.sqlite"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    conn = sqlite3.connect(path)
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audio_chunks (
            id INTEGER PRIMARY KEY,
            captured_at TEXT NOT NULL,
            duration_sec REAL NOT NULL,
            source TEXT NOT NULL,
            transcript TEXT NOT NULL,
            audio_path TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS audio_fts USING fts5(
            transcript,
            content='audio_chunks',
            content_rowid='id'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            title TEXT NOT NULL,
            transcript TEXT NOT NULL,
            summary TEXT,
            action_items TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS automations_log (
            id INTEGER PRIMARY KEY,
            executed_at TEXT NOT NULL,
            automation_name TEXT NOT NULL,
            result TEXT NOT NULL
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


def insert_audio_chunk(
    conn: sqlite3.Connection,
    duration_sec: float,
    source: str,
    transcript: str,
    audio_path: str | None = None,
) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.execute(
        """
        INSERT INTO audio_chunks (captured_at, duration_sec, source, transcript, audio_path)
        VALUES (?, ?, ?, ?, ?)
        """,
        (now, duration_sec, source, transcript, audio_path),
    )
    rowid = int(cur.lastrowid)
    conn.execute(
        "INSERT INTO audio_fts (rowid, transcript) VALUES (?, ?)",
        (rowid, transcript),
    )
    conn.commit()
    return rowid


def insert_meeting(
    conn: sqlite3.Connection,
    title: str,
    transcript: str,
    summary: str | None = None,
    action_items: str | None = None,
    started_at: str | None = None,
    ended_at: str | None = None,
) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    start = started_at or now
    end = ended_at or now
    cur = conn.execute(
        """
        INSERT INTO meetings (started_at, ended_at, title, transcript, summary, action_items)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (start, end, title, transcript, summary, action_items),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_meetings(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT id, started_at, ended_at, title, summary, action_items, length(transcript) as transcript_chars
            FROM meetings
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
    )


def insert_automation_run(
    conn: sqlite3.Connection,
    automation_name: str,
    result: str,
) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.execute(
        """
        INSERT INTO automations_log (executed_at, automation_name, result)
        VALUES (?, ?, ?)
        """,
        (now, automation_name, result),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_automations(conn: sqlite3.Connection, limit: int = 15) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT id, executed_at, automation_name, result
            FROM automations_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
    )


def list_recent_frames(conn: sqlite3.Connection, limit: int = 30) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, captured_at, length(text) as char_count, substr(text, 1, 300) as preview, image_path
        FROM frames
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in rows]


def get_stats(conn: sqlite3.Connection) -> dict:
    frame_count = conn.execute("SELECT COUNT(*) FROM frames").fetchone()[0]
    audio_count = conn.execute("SELECT COUNT(*) FROM audio_chunks").fetchone()[0]
    meeting_count = conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
    automation_count = conn.execute("SELECT COUNT(*) FROM automations_log").fetchone()[0]
    latest_frame = conn.execute("SELECT captured_at FROM frames ORDER BY id DESC LIMIT 1").fetchone()
    latest_ts = latest_frame[0] if latest_frame else "Never"
    
    db_size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "frames_count": frame_count,
        "audio_chunks_count": audio_count,
        "meetings_count": meeting_count,
        "automations_count": automation_count,
        "latest_capture": latest_ts,
        "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
    }

