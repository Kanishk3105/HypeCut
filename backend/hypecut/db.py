from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

# The whole application shares one sqlite3.Connection across the FastAPI
# threads and the job-worker thread. Python's sqlite3 module is not safe for
# concurrent use of a single connection (implicit transactions interleave and
# commit() then raises "cannot commit - no transaction is active"), so every
# touch of the connection goes through this reentrant lock.
CONN_LOCK = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('youtube', 'local')),
    source_ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled', 'cancel_requested')),
    stage TEXT NOT NULL DEFAULT 'validation',
    progress REAL CHECK (progress IS NULL OR (progress >= 0 AND progress <= 100)),
    message TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL DEFAULT '{}',
    result TEXT,
    error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_data_dir() -> Path:
    env = os.environ.get("HYPECUT_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "data"


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = default_data_dir() / "hypecut.db"
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    with CONN_LOCK:
        conn.executescript(SCHEMA)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(projects)")}
        if "metadata" not in columns:
            conn.execute("ALTER TABLE projects ADD COLUMN metadata TEXT")
        conn.commit()


def _row_to_project(row: sqlite3.Row) -> dict:
    project = dict(row)
    raw = project.get("metadata")
    if isinstance(raw, str) and raw:
        try:
            project["metadata"] = json.loads(raw)
        except json.JSONDecodeError:
            project["metadata"] = None
    return project


def set_project_metadata(conn: sqlite3.Connection, project_id: str, data: dict) -> None:
    with CONN_LOCK:
        conn.execute(
            "UPDATE projects SET metadata = ?, updated_at = ? WHERE id = ?",
            (json.dumps(data), utcnow(), project_id),
        )
        conn.commit()


def new_id() -> str:
    return uuid.uuid4().hex


def create_project(
    conn: sqlite3.Connection, name: str, source_type: str, source_ref: str, status: str = "created"
) -> dict:
    if source_type not in ("youtube", "local"):
        raise ValueError("source_type must be 'youtube' or 'local'")
    now = utcnow()
    project_id = new_id()
    with CONN_LOCK:
        conn.execute(
            "INSERT INTO projects (id, name, source_type, source_ref, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, name, source_type, source_ref, status, now, now),
        )
        conn.commit()
    return get_project(conn, project_id)


def get_project(conn: sqlite3.Connection, project_id: str) -> dict | None:
    with CONN_LOCK:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _row_to_project(row) if row else None


def list_projects(conn: sqlite3.Connection) -> list[dict]:
    with CONN_LOCK:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return [_row_to_project(r) for r in rows]


def update_project(conn: sqlite3.Connection, project_id: str, **fields: str) -> dict | None:
    allowed = {"name", "status", "source_ref"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_project(conn, project_id)
    updates["updated_at"] = utcnow()
    sets = ", ".join(f"{k} = ?" for k in updates)
    with CONN_LOCK:
        cur = conn.execute(
            f"UPDATE projects SET {sets} WHERE id = ?",  # noqa: S608 - keys are allow-listed above
            (*updates.values(), project_id),
        )
        conn.commit()
    if cur.rowcount == 0:
        return None
    return get_project(conn, project_id)


def delete_project(conn: sqlite3.Connection, project_id: str) -> bool:
    with CONN_LOCK:
        cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
    return cur.rowcount > 0


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    with CONN_LOCK:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    with CONN_LOCK:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None
