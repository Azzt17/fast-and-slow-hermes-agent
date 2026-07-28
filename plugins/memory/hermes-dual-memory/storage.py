"""SQLite storage helpers for hot sessions and the memory shadow index."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

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

MEMORY_INDEX_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_index (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    mem0_id           TEXT NOT NULL UNIQUE,
    session_id        TEXT NOT NULL,
    memory_type       TEXT,
    tier              TEXT DEFAULT 'warm',
    status            TEXT DEFAULT 'candidate',
    t_valid           DATETIME,
    t_invalid         DATETIME,
    t_created         DATETIME DEFAULT CURRENT_TIMESTAMP,
    importance_score  INTEGER DEFAULT 0,
    stability         REAL DEFAULT 1.0,
    access_count      INTEGER DEFAULT 0,
    last_accessed     DATETIME,
    superseded_by     TEXT,
    flagged_reason    TEXT
)
"""

MEMORY_INDEX_STATUS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_memory_status
ON memory_index(status, tier)
"""

MEMORY_ENTITIES_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_entities (
    memory_index_id  INTEGER NOT NULL,
    entity_id        TEXT NOT NULL,
    entity_type      TEXT,
    entity_label     TEXT NOT NULL,
    entity_key       TEXT NOT NULL,
    PRIMARY KEY (memory_index_id, entity_key),
    FOREIGN KEY (memory_index_id) REFERENCES memory_index(id)
)
"""

MEMORY_ENTITIES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_memory_entity_key
ON memory_entities(entity_key, memory_index_id)
"""

MEMORY_RELATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_relations (
    memory_index_id   INTEGER NOT NULL,
    source_entity_key TEXT NOT NULL,
    target_entity_key TEXT NOT NULL,
    relation          TEXT NOT NULL,
    relation_key      TEXT NOT NULL,
    UNIQUE (memory_index_id, source_entity_key, target_entity_key, relation_key),
    FOREIGN KEY (memory_index_id) REFERENCES memory_index(id)
)
"""

MEMORY_RELATIONS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_memory_relation_claim
ON memory_relations(source_entity_key, relation_key, memory_index_id)
"""

MAINTENANCE_STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS maintenance_state (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
)
"""

MEMORY_LIFECYCLE_EVENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_lifecycle_events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_index_id  INTEGER NOT NULL,
    event_type       TEXT NOT NULL,
    occurred_at      DATETIME NOT NULL,
    FOREIGN KEY (memory_index_id) REFERENCES memory_index(id)
)
"""

MEMORY_LIFECYCLE_EVENTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_memory_lifecycle_event
ON memory_lifecycle_events(memory_index_id, event_type, occurred_at)
"""

MEMORY_COMPACTION_SOURCES_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_compaction_sources (
    compacted_memory_index_id  INTEGER NOT NULL,
    source_memory_index_id     INTEGER NOT NULL,
    created_at                 DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (compacted_memory_index_id, source_memory_index_id),
    FOREIGN KEY (compacted_memory_index_id) REFERENCES memory_index(id),
    FOREIGN KEY (source_memory_index_id) REFERENCES memory_index(id)
)
"""


def resolve_hot_sessions_db_path(base_path: str | Path) -> Path:
    """Resolve the shared SQLite file used by this provider."""

    path = Path(base_path)
    if path.exists() and path.is_dir():
        return path / "hot_sessions.sqlite3"
    if not path.exists() and not path.suffix:
        return path / "hot_sessions.sqlite3"
    return path


def normalize_claim_key(value: object) -> str:
    """Return a stable key for conservative entity and relation matching."""

    return " ".join(str(value or "").strip().casefold().split())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def db_timestamp(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat()


def parse_db_timestamp(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalized_claims(
    entities: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Normalize report relations to entity-label based claims."""

    entity_keys: dict[str, str] = {}
    for entity in entities:
        entity_id = normalize_claim_key(entity.get("id"))
        entity_label = normalize_claim_key(entity.get("label"))
        entity_key = entity_id or entity_label
        if not entity_key:
            continue
        if entity_id:
            entity_keys[entity_id] = entity_key
        if entity_label:
            entity_keys[entity_label] = entity_key

    claims: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for relation in relations:
        source_ref = normalize_claim_key(relation.get("source"))
        target_ref = normalize_claim_key(relation.get("target"))
        relation_key = normalize_claim_key(relation.get("relation"))
        source_key = entity_keys.get(source_ref, source_ref)
        target_key = entity_keys.get(target_ref, target_ref)
        claim_key = (source_key, relation_key, target_key)
        if not all(claim_key) or claim_key in seen:
            continue
        seen.add(claim_key)
        claims.append(
            {
                "source": source_key,
                "relation": relation_key,
                "target": target_key,
            }
        )
    return claims


class HotSessionStore:
    """SQLite wrapper for hot turns and shadow policy metadata."""

    def __init__(self, base_path: str | Path):
        self.db_path = resolve_hot_sessions_db_path(base_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            yield conn
        except BaseException:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self.connect() as conn:
            conn.execute(HOT_SESSIONS_SCHEMA)
            conn.execute(HOT_SESSIONS_INDEX)
            conn.execute(MEMORY_INDEX_SCHEMA)
            conn.execute(MEMORY_INDEX_STATUS_INDEX)
            conn.execute(MEMORY_ENTITIES_SCHEMA)
            conn.execute(MEMORY_ENTITIES_INDEX)
            conn.execute(MEMORY_RELATIONS_SCHEMA)
            conn.execute(MEMORY_RELATIONS_INDEX)
            conn.execute(MAINTENANCE_STATE_SCHEMA)
            conn.execute(MEMORY_LIFECYCLE_EVENTS_SCHEMA)
            conn.execute(MEMORY_LIFECYCLE_EVENTS_INDEX)
            conn.execute(MEMORY_COMPACTION_SOURCES_SCHEMA)
            conn.execute(
                """
                UPDATE memory_index
                SET stability = CASE
                    WHEN importance_score / 2.0 < 0.5 THEN 0.5
                    ELSE importance_score / 2.0
                END
                WHERE access_count = 0
                """
            )

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
                (session_id, role, content, token_count, 1 if consolidated else 0),
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

    @staticmethod
    def normalized_claims(
        entities: Sequence[Mapping[str, Any]],
        relations: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, str]]:
        """Expose normalized claims through the store integration boundary."""

        return normalized_claims(entities, relations)

    def find_active_semantic_candidates(
        self,
        entities: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        """Find active trusted semantic memories sharing an entity."""

        entity_keys = sorted(
            {
                key
                for entity in entities
                for key in (
                    normalize_claim_key(entity.get("id")),
                    normalize_claim_key(entity.get("label")),
                )
                if key
            }
        )
        if not entity_keys:
            return []

        placeholders = ", ".join("?" for _ in entity_keys)
        with self.connect() as conn:
            memory_rows = conn.execute(
                f"""
                SELECT DISTINCT
                    memory_index.id,
                    memory_index.mem0_id,
                    memory_index.session_id
                FROM memory_index
                JOIN memory_entities
                  ON memory_entities.memory_index_id = memory_index.id
                WHERE memory_index.memory_type = 'semantic'
                  AND memory_index.status = 'trusted'
                  AND memory_index.t_invalid IS NULL
                  AND memory_entities.entity_key IN ({placeholders})
                ORDER BY memory_index.id ASC
                """,
                entity_keys,
            ).fetchall()
            if not memory_rows:
                return []

            memory_ids = [int(row["id"]) for row in memory_rows]
            relation_placeholders = ", ".join("?" for _ in memory_ids)
            relation_rows = conn.execute(
                f"""
                SELECT
                    memory_index_id,
                    source_entity_key,
                    target_entity_key,
                    relation_key
                FROM memory_relations
                WHERE memory_index_id IN ({relation_placeholders})
                ORDER BY rowid ASC
                """,
                memory_ids,
            ).fetchall()

        relations_by_memory: dict[int, list[dict[str, str]]] = {
            memory_id: [] for memory_id in memory_ids
        }
        for row in relation_rows:
            relations_by_memory[int(row["memory_index_id"])].append(
                {
                    "source": str(row["source_entity_key"]),
                    "relation": str(row["relation_key"]),
                    "target": str(row["target_entity_key"]),
                }
            )
        return [
            {
                "mem0_id": str(row["mem0_id"]),
                "session_id": str(row["session_id"]),
                "relations": relations_by_memory[int(row["id"])],
            }
            for row in memory_rows
        ]

    def record_memory(
        self,
        *,
        mem0_id: str,
        session_id: str,
        memory_type: str,
        importance_score: int | float,
        entities: Sequence[Mapping[str, Any]],
        relations: Sequence[Mapping[str, Any]],
        status: str = "trusted",
        flagged_reason: str | None = None,
        supersedes: Sequence[str] = (),
    ) -> int:
        """Record a Mem0 essence and atomically invalidate old shadows."""

        normalized_mem0_id = str(mem0_id).strip()
        if not normalized_mem0_id:
            raise ValueError("mem0_id must not be empty")

        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO memory_index (
                    mem0_id,
                    session_id,
                    memory_type,
                    status,
                    t_valid,
                    importance_score,
                    stability,
                    flagged_reason
                )
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
                """,
                (
                    normalized_mem0_id,
                    session_id,
                    memory_type,
                    "candidate",
                    importance_score,
                    max(float(importance_score) / 2.0, 0.5),
                    flagged_reason,
                ),
            )
            memory_index_id = int(cursor.lastrowid)

            entity_rows: list[tuple[int, str, str, str, str]] = []
            seen_entity_keys: set[str] = set()
            for entity in entities:
                entity_id = str(entity.get("id") or "").strip()
                entity_type = str(entity.get("type") or "").strip()
                entity_label = str(entity.get("label") or "").strip()
                for entity_key in {
                    normalize_claim_key(entity_id),
                    normalize_claim_key(entity_label),
                } - {""}:
                    if entity_key in seen_entity_keys:
                        continue
                    seen_entity_keys.add(entity_key)
                    entity_rows.append(
                        (memory_index_id, entity_id, entity_type, entity_label or entity_id, entity_key)
                    )
            if entity_rows:
                conn.executemany(
                    """
                    INSERT INTO memory_entities (
                        memory_index_id,
                        entity_id,
                        entity_type,
                        entity_label,
                        entity_key
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    entity_rows,
                )

            claim_rows = [
                (
                    memory_index_id,
                    claim["source"],
                    claim["target"],
                    claim["relation"],
                    claim["relation"],
                )
                for claim in self.normalized_claims(entities, relations)
            ]
            if claim_rows:
                conn.executemany(
                    """
                    INSERT INTO memory_relations (
                        memory_index_id,
                        source_entity_key,
                        target_entity_key,
                        relation,
                        relation_key
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    claim_rows,
                )
            if status != "candidate":
                self._finalize_memory_in_connection(
                    conn,
                    mem0_id=normalized_mem0_id,
                    status=status,
                    flagged_reason=flagged_reason,
                    supersedes=supersedes,
                )
            return memory_index_id

    @staticmethod
    def _finalize_memory_in_connection(
        conn: sqlite3.Connection,
        *,
        mem0_id: str,
        status: str,
        flagged_reason: str | None,
        supersedes: Sequence[str],
    ) -> None:
        if status not in ("trusted", "quarantined"):
            raise ValueError("final memory status must be trusted or quarantined")
        if status == "trusted" and supersedes:
            placeholders = ", ".join("?" for _ in supersedes)
            conn.execute(
                f"""
                UPDATE memory_index
                SET
                    t_invalid = CURRENT_TIMESTAMP,
                    superseded_by = ?
                WHERE mem0_id IN ({placeholders})
                  AND memory_type = 'semantic'
                  AND t_invalid IS NULL
                """,
                (mem0_id, *supersedes),
            )
        result = conn.execute(
            """
            UPDATE memory_index
            SET status = ?, flagged_reason = ?
            WHERE mem0_id = ? AND status = 'candidate'
            """,
            (status, flagged_reason, mem0_id),
        )
        if int(result.rowcount) != 1:
            raise ValueError("candidate shadow was not available for admission finalization")

    def finalize_memory_admission(
        self,
        *,
        mem0_id: str,
        status: str,
        flagged_reason: str | None = None,
        supersedes: Sequence[str] = (),
    ) -> None:
        """Finalize a persisted candidate and atomically apply trusted supersedes."""

        with self.connect() as conn:
            self._finalize_memory_in_connection(
                conn,
                mem0_id=mem0_id,
                status=status,
                flagged_reason=flagged_reason,
                supersedes=supersedes,
            )

    def retrieval_states(self, mem0_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        """Return shadow policy state; missing IDs are legacy data."""

        unique_ids = sorted({str(mem0_id) for mem0_id in mem0_ids if str(mem0_id).strip()})
        if not unique_ids:
            return {}
        placeholders = ", ".join("?" for _ in unique_ids)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT mem0_id, status, t_invalid
                FROM memory_index
                WHERE mem0_id IN ({placeholders})
                """,
                unique_ids,
            ).fetchall()
        return {
            str(row["mem0_id"]): {
                "status": str(row["status"]),
                "t_invalid": row["t_invalid"],
            }
            for row in rows
        }

    def record_accesses(
        self,
        mem0_ids: Sequence[str],
        *,
        accessed_at: datetime | None = None,
    ) -> dict[str, str]:
        """Record visible retrievals and promote eligible cold episodic rows."""

        unique_ids = sorted({str(mem0_id) for mem0_id in mem0_ids if str(mem0_id).strip()})
        if not unique_ids:
            return {}
        now = accessed_at or utc_now()
        now_text = db_timestamp(now)
        window_start = db_timestamp(now - timedelta(days=7))
        placeholders = ", ".join("?" for _ in unique_ids)
        promoted: dict[str, str] = {}
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, mem0_id, memory_type, tier
                FROM memory_index
                WHERE mem0_id IN ({placeholders})
                  AND status = 'trusted'
                  AND t_invalid IS NULL
                """,
                unique_ids,
            ).fetchall()
            for row in rows:
                memory_index_id = int(row["id"])
                conn.execute(
                    """
                    UPDATE memory_index
                    SET
                        access_count = access_count + 1,
                        last_accessed = ?,
                        stability = MAX(stability, 0.5) * 1.5
                    WHERE id = ?
                    """,
                    (now_text, memory_index_id),
                )
                conn.execute(
                    """
                    INSERT INTO memory_lifecycle_events (
                        memory_index_id,
                        event_type,
                        occurred_at
                    )
                    VALUES (?, 'access', ?)
                    """,
                    (memory_index_id, now_text),
                )
                if row["memory_type"] != "episodic" or row["tier"] != "cold":
                    continue
                demoted = conn.execute(
                    """
                    SELECT occurred_at
                    FROM memory_lifecycle_events
                    WHERE memory_index_id = ? AND event_type = 'demoted'
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (memory_index_id,),
                ).fetchone()
                if demoted is None:
                    continue
                demoted_at = str(demoted["occurred_at"])
                parsed_demoted_at = parse_db_timestamp(demoted_at)
                if parsed_demoted_at is None or now > parsed_demoted_at + timedelta(days=7):
                    continue
                access_row = conn.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM memory_lifecycle_events
                    WHERE memory_index_id = ?
                      AND event_type = 'access'
                      AND occurred_at >= ?
                      AND occurred_at >= ?
                    """,
                    (memory_index_id, demoted_at, window_start),
                ).fetchone()
                if access_row is not None and int(access_row["count"]) >= 2:
                    conn.execute(
                        "UPDATE memory_index SET tier = 'warm' WHERE id = ?",
                        (memory_index_id,),
                    )
                    conn.execute(
                        """
                        INSERT INTO memory_lifecycle_events (
                            memory_index_id,
                            event_type,
                            occurred_at
                        )
                        VALUES (?, 'promoted', ?)
                        """,
                        (memory_index_id, now_text),
                    )
                    promoted[str(row["mem0_id"])] = "warm"
        return promoted

    def claim_decay_cycle(
        self,
        *,
        now: datetime | None = None,
        interval: timedelta = timedelta(hours=24),
    ) -> bool:
        """Atomically claim a full maintenance cycle if the interval elapsed."""

        current = now or utc_now()
        threshold = current - interval
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO maintenance_state (key, value)
                VALUES ('last_decay_run', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                WHERE maintenance_state.value <= ?
                """,
                (db_timestamp(current), db_timestamp(threshold)),
            )
        return int(cursor.rowcount) == 1

    def get_maintenance_state(self, key: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM maintenance_state WHERE key = ?",
                (key,),
            ).fetchone()
        return str(row["value"]) if row is not None else None

    def episodic_decay_candidates(self) -> list[dict[str, Any]]:
        """Return active trusted episodic shadows eligible for decay."""

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    mem0_id,
                    tier,
                    t_created,
                    last_accessed,
                    stability,
                    importance_score
                FROM memory_index
                WHERE memory_type = 'episodic'
                  AND status = 'trusted'
                  AND t_invalid IS NULL
                ORDER BY id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def demote_memories(
        self,
        mem0_ids: Sequence[str],
        *,
        demoted_at: datetime | None = None,
    ) -> int:
        """Demote active trusted episodic rows and record lifecycle events."""

        unique_ids = sorted({str(mem0_id) for mem0_id in mem0_ids if str(mem0_id).strip()})
        if not unique_ids:
            return 0
        now_text = db_timestamp(demoted_at or utc_now())
        placeholders = ", ".join("?" for _ in unique_ids)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id
                FROM memory_index
                WHERE mem0_id IN ({placeholders})
                  AND memory_type = 'episodic'
                  AND status = 'trusted'
                  AND t_invalid IS NULL
                  AND tier != 'cold'
                """,
                unique_ids,
            ).fetchall()
            memory_ids = [int(row["id"]) for row in rows]
            if not memory_ids:
                return 0
            id_placeholders = ", ".join("?" for _ in memory_ids)
            conn.execute(
                f"UPDATE memory_index SET tier = 'cold' WHERE id IN ({id_placeholders})",
                memory_ids,
            )
            conn.executemany(
                """
                INSERT INTO memory_lifecycle_events (
                    memory_index_id,
                    event_type,
                    occurred_at
                )
                VALUES (?, 'demoted', ?)
                """,
                [(memory_id, now_text) for memory_id in memory_ids],
            )
        return len(memory_ids)

    def active_cold_memories(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, mem0_id, session_id, importance_score
                FROM memory_index
                WHERE memory_type = 'episodic'
                  AND tier = 'cold'
                  AND status = 'trusted'
                  AND t_invalid IS NULL
                ORDER BY id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def record_compaction(
        self,
        *,
        compacted_mem0_id: str,
        session_id: str,
        importance_score: int | float,
        source_mem0_ids: Sequence[str],
        status: str = "trusted",
        flagged_reason: str | None = None,
        compacted_at: datetime | None = None,
    ) -> int:
        """Create a warm compacted shadow and invalidate sources with lineage."""

        source_ids = sorted({str(mem0_id) for mem0_id in source_mem0_ids if str(mem0_id).strip()})
        if len(source_ids) < 2:
            raise ValueError("cold compaction requires at least two source memories")
        now_text = db_timestamp(compacted_at or utc_now())
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO memory_index (
                    mem0_id,
                    session_id,
                    memory_type,
                    tier,
                    status,
                    t_valid,
                    t_created,
                    importance_score,
                    stability,
                    flagged_reason
                )
                VALUES (?, ?, 'episodic', 'warm', 'candidate', ?, ?, ?, ?, ?)
                """,
                (
                    compacted_mem0_id,
                    session_id,
                    now_text,
                    now_text,
                    importance_score,
                    max(float(importance_score) / 2.0, 0.5),
                    flagged_reason,
                ),
            )
            compacted_index_id = int(cursor.lastrowid)
            if status == "quarantined":
                conn.execute(
                    "UPDATE memory_index SET status = 'quarantined' WHERE id = ?",
                    (compacted_index_id,),
                )
                return compacted_index_id
            if status != "trusted":
                raise ValueError("compacted memory status must be trusted or quarantined")
            placeholders = ", ".join("?" for _ in source_ids)
            source_rows = conn.execute(
                f"""
                SELECT id, mem0_id
                FROM memory_index
                WHERE mem0_id IN ({placeholders})
                  AND memory_type = 'episodic'
                  AND tier = 'cold'
                  AND status = 'trusted'
                  AND t_invalid IS NULL
                """,
                source_ids,
            ).fetchall()
            if len(source_rows) != len(source_ids):
                raise ValueError("cold compaction sources changed before lineage write")
            conn.executemany(
                """
                UPDATE memory_index
                SET t_invalid = ?, superseded_by = ?
                WHERE id = ?
                """,
                [
                    (now_text, compacted_mem0_id, int(row["id"]))
                    for row in source_rows
                ],
            )
            conn.executemany(
                """
                INSERT INTO memory_compaction_sources (
                    compacted_memory_index_id,
                    source_memory_index_id
                )
                VALUES (?, ?)
                """,
                [
                    (compacted_index_id, int(row["id"]))
                    for row in source_rows
                ],
            )
            conn.execute(
                "UPDATE memory_index SET status = 'trusted' WHERE id = ?",
                (compacted_index_id,),
            )
        return compacted_index_id

    def fetch_compaction_sources(self, compacted_mem0_id: str) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT source.mem0_id
                FROM memory_compaction_sources
                JOIN memory_index AS compacted
                  ON compacted.id = memory_compaction_sources.compacted_memory_index_id
                JOIN memory_index AS source
                  ON source.id = memory_compaction_sources.source_memory_index_id
                WHERE compacted.mem0_id = ?
                ORDER BY source.id ASC
                """,
                (compacted_mem0_id,),
            ).fetchall()
        return [str(row["mem0_id"]) for row in rows]

    def policy_revision(self) -> str:
        """Return a deterministic fingerprint of retrieval-relevant shadow state."""

        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(GROUP_CONCAT(policy_value, '|'), '') AS revision
                FROM (
                    SELECT
                        id || ':' || status || ':' || COALESCE(t_invalid, '')
                        || ':' || COALESCE(superseded_by, '') AS policy_value
                    FROM memory_index
                    ORDER BY id ASC
                )
                """
            ).fetchone()
        return str(row["revision"] if row is not None else "")

    def fetch_memory_index(self) -> list[dict[str, Any]]:
        """Return all shadow rows in insertion order for audit and tests."""

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    mem0_id,
                    session_id,
                    memory_type,
                    tier,
                    status,
                    t_valid,
                    t_invalid,
                    t_created,
                    importance_score,
                    stability,
                    access_count,
                    last_accessed,
                    superseded_by,
                    flagged_reason
                FROM memory_index
                ORDER BY id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]
