"""SQLite storage helpers for the Hermes hot session log.

This module implements the schema from §3.2 of the architecture spec and
provides a small, explicit API for future phase-1 integration.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

HOT_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS hot_sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL,
    timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
    role          TEXT,
    content       TEXT NOT NULL,
    token_count   INTEGER,
    consolidated  BOOLEAN DEFAULT 0
)
"""

HOT_SESSIONS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_hot_session
ON hot_sessions(session_id, consolidated)
"""


def resolve_hot_sessions_db_path(base_path: str | Path) -> Path:
    """Resolve the SQLite file path for the hot-session store.

    The phase-1 caller will pass a Hermes home directory. If a file path is
    passed instead, it is used as-is.
    """

    path = Path(base_path)
    if path.exists() and path.is_dir():
        return path / "hot_sessions.sqlite3"
    if not path.exists() and not path.suffix:
        return path / "hot_sessions.sqlite3"
    return path


class HotSessionStore:
    """Small SQLite wrapper for the raw hot session log."""

    def __init__(self, base_path: str | Path):
        self.db_path = resolve_hot_sessions_db_path(base_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self.connect() as conn:
            conn.execute(HOT_SESSIONS_SCHEMA)
            conn.execute(HOT_SESSIONS_INDEX)

    def add_turn(
        self,
        session_id: str,
        content: str,
        role: str | None = None,
        token_count: int | None = None,
        consolidated: bool = False,
    ) -> int:
        """Insert a raw turn into hot_sessions and return the new row id."""

        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO hot_sessions (
                    session_id,
                    role,
                    content,
                    token_count,
                    consolidated
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content,
                    token_count,
                    1 if consolidated else 0,
                ),
            )
            return int(cursor.lastrowid)

    def fetch_turns(
        self,
        session_id: str,
        consolidated: bool = False,
    ) -> list[dict[str, object]]:
        """Fetch turns for one session."""

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    session_id,
                    timestamp,
                    role,
                    content,
                    token_count,
                    consolidated
                FROM hot_sessions
                WHERE session_id = ? AND consolidated = ?
                ORDER BY id ASC
                """,
                (session_id, 1 if consolidated else 0),
            ).fetchall()

        return [dict(row) for row in rows]

    def mark_consolidated(self, session_id: str, row_ids: Sequence[int] | None = None) -> int:
        """Mark rows as consolidated and return the number of affected rows."""

        with self.connect() as conn:
            if row_ids is not None:
                if len(row_ids) == 0:
                    return 0
                placeholders = ", ".join("?" for _ in row_ids)
                result = conn.execute(
                    f"""
                    UPDATE hot_sessions
                    SET consolidated = 1
                    WHERE session_id = ? AND id IN ({placeholders})
                    """,
                    (session_id, *row_ids),
                )
            else:
                result = conn.execute(
                    """
                    UPDATE hot_sessions
                    SET consolidated = 1
                    WHERE session_id = ?
                    """,
                    (session_id,),
                )
            return int(result.rowcount)

    def pending_count(self, session_id: str) -> int:
        """Count rows that still need consolidation."""

        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM hot_sessions
                WHERE session_id = ? AND consolidated = 0
                """,
                (session_id,),
            ).fetchone()
        return int(row["count"] if row is not None else 0)
