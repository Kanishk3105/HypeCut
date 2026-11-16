from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Callable

from . import db as dbmod

logger = logging.getLogger("hypecut.jobs")

STAGES = (
    "validation",
    "metadata",
    "download",
    "media_inspection",
    "replay_heatmap",
    "transcription",
    "audio_analysis",
    "visual_analysis",
    "audience_intelligence",
    "highlight_scoring",
    "candidate_generation",
    "caption_preparation",
    "rendering",
    "export_verification",
)

TERMINAL_STATUSES = ("succeeded", "failed", "cancelled")

JobContextReporter = Callable[[str, float | None, str], None]


class JobCancelled(Exception):
    pass


@dataclass
class JobContext:
    job_id: str
    _conn: sqlite3.Connection
    _queue: "JobQueue"

    def report(self, stage: str, progress: float | None = None, message: str = "") -> None:
        if stage not in STAGES:
            raise ValueError(f"unknown stage: {stage}")
        if progress is not None and not (0 <= progress <= 100):
            raise ValueError("progress must be between 0 and 100")
        self._queue._update(
            self._conn,
            self.job_id,
            stage=stage,
            progress=progress,
            message=message,
        )

    def check_cancelled(self) -> None:
        if self._queue._is_cancel_requested(self._conn, self.job_id):
            raise JobCancelled()


Handler = Callable[[JobContext, dict], dict | None]


class JobQueue:
    """Persistent single-lane job queue backed by SQLite."""

    def __init__(self, conn: sqlite3.Connection, poll_interval: float = 0.05) -> None:
        self._conn = conn
        self._poll_interval = poll_interval
        self._handlers: dict[str, Handler] = {}
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()
        self._active_job_id: str | None = None

    def register(self, job_type: str, handler: Handler) -> None:
        self._handlers[job_type] = handler

    def has(self, job_type: str) -> bool:
        return job_type in self._handlers

    def recover_interrupted(self) -> int:
        cur = self._conn.execute(
            "UPDATE jobs SET status = 'queued', message = ?, updated_at = ? "
            "WHERE status IN ('running', 'cancel_requested')",
            ("requeued after application restart", dbmod.utcnow()),
        )
        self._conn.commit()
        if cur.rowcount:
            logger.info("requeued %d interrupted job(s)", cur.rowcount)
        return cur.rowcount

    def enqueue(
        self,
        job_type: str,
        project_id: str | None = None,
        payload: dict | None = None,
    ) -> dict:
        if job_type not in self._handlers:
            raise ValueError(f"no handler registered for job type: {job_type}")
        job_id = dbmod.new_id()
        now = dbmod.utcnow()
        self._conn.execute(
            "INSERT INTO jobs (id, project_id, type, status, stage, payload, created_at, updated_at) "
            "VALUES (?, ?, ?, 'queued', 'validation', ?, ?, ?)",
            (job_id, project_id, job_type, json.dumps(payload or {}), now, now),
        )
        self._conn.commit()
        self._wake.set()
        return self.get(job_id)

    def get(self, job_id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _job_to_dict(row) if row else None

    def list(self, status: str | None = None, project_id: str | None = None) -> list[dict]:
        query = "SELECT * FROM jobs"
        clauses: list[str] = []
        params: list[str] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [_job_to_dict(r) for r in rows]

    def cancel(self, job_id: str) -> dict | None:
        with self._lock:
            job = self.get(job_id)
            if job is None:
                return None
            if job["status"] == "queued":
                self._conn.execute(
                    "UPDATE jobs SET status = 'cancelled', message = ?, updated_at = ? WHERE id = ?",
                    ("cancelled before start", dbmod.utcnow(), job_id),
                )
                self._conn.commit()
            elif job["status"] in ("running", "cancel_requested"):
                self._conn.execute(
                    "UPDATE jobs SET status = 'cancel_requested', cancel_requested = 1, updated_at = ? "
                    "WHERE id = ?",
                    (dbmod.utcnow(), job_id),
                )
                self._conn.commit()
            return self.get(job_id)

    def retry(self, job_id: str) -> dict | None:
        with self._lock:
            job = self.get(job_id)
            if job is None:
                return None
            if job["status"] not in ("failed", "cancelled"):
                raise ValueError(f"only failed or cancelled jobs can be retried (was {job['status']})")
            self._conn.execute(
                "UPDATE jobs SET status = 'queued', stage = 'validation', progress = NULL, "
                "message = ?, error = NULL, cancel_requested = 0, attempts = attempts, updated_at = ? "
                "WHERE id = ?",
                ("requeued by user", dbmod.utcnow(), job_id),
            )
            self._conn.commit()
            self._wake.set()
            return self.get(job_id)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.recover_interrupted()
        self._stopping.clear()
        self._thread = threading.Thread(target=self._run_loop, name="hypecut-job-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stopping.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def wait_idle(self, timeout: float = 10.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM jobs WHERE status IN ('queued', 'running', 'cancel_requested')"
            ).fetchone()
            if row["n"] == 0:
                return True
            time.sleep(0.02)
        return False

    def _run_loop(self) -> None:
        while not self._stopping.is_set():
            job_row = self._conn.execute(
                "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            if job_row is None:
                self._wake.wait(timeout=self._poll_interval)
                self._wake.clear()
                continue
            self._execute(dict(job_row))

    def _execute(self, job: dict) -> None:
        job_id = job["id"]
        with self._lock:
            cur = self._conn.execute(
                "UPDATE jobs SET status = 'running', attempts = attempts + 1, updated_at = ? "
                "WHERE id = ? AND status = 'queued'",
                (dbmod.utcnow(), job_id),
            )
            self._conn.commit()
            if cur.rowcount == 0:
                return
            self._active_job_id = job_id

        handler = self._handlers.get(job["type"])
        ctx = JobContext(job_id=job_id, _conn=self._conn, _queue=self)
        try:
            if handler is None:
                raise RuntimeError(f"no handler for job type {job['type']}")
            if self._is_cancel_requested(self._conn, job_id):
                raise JobCancelled()
            payload = json.loads(job.get("payload") or "{}")
            result = handler(ctx, payload)
            if self._is_cancel_requested(self._conn, job_id):
                self._finish_cancelled(job_id)
            else:
                self._conn.execute(
                    "UPDATE jobs SET status = 'succeeded', progress = 100, message = ?, result = ?, "
                    "updated_at = ? WHERE id = ?",
                    ("completed", json.dumps(result) if result is not None else None, dbmod.utcnow(), job_id),
                )
                self._conn.commit()
        except JobCancelled:
            self._finish_cancelled(job_id)
        except Exception as exc:  # noqa: BLE001 - job isolation requires catching all
            logger.exception("job %s failed", job_id)
            if self._is_cancel_requested(self._conn, job_id):
                self._finish_cancelled(job_id)
            else:
                self._conn.execute(
                    "UPDATE jobs SET status = 'failed', error = ?, message = ?, updated_at = ? WHERE id = ?",
                    (str(exc)[:2000], "job failed", dbmod.utcnow(), job_id),
                )
                self._conn.commit()
        finally:
            with self._lock:
                self._active_job_id = None

    def _finish_cancelled(self, job_id: str) -> None:
        self._conn.execute(
            "UPDATE jobs SET status = 'cancelled', message = ?, updated_at = ? WHERE id = ?",
            ("cancelled by user", dbmod.utcnow(), job_id),
        )
        self._conn.commit()

    @staticmethod
    def _update(
        conn: sqlite3.Connection,
        job_id: str,
        stage: str | None = None,
        progress: float | None = None,
        message: str | None = None,
    ) -> None:
        sets: list[str] = []
        params: list[object] = []
        if stage is not None:
            sets.append("stage = ?")
            params.append(stage)
        if progress is not None:
            sets.append("progress = ?")
            params.append(progress)
        if message is not None:
            sets.append("message = ?")
            params.append(message)
        if not sets:
            return
        sets.append("updated_at = ?")
        params.append(dbmod.utcnow())
        params.append(job_id)
        conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", params)  # noqa: S608
        conn.commit()

    @staticmethod
    def _is_cancel_requested(conn: sqlite3.Connection, job_id: str) -> bool:
        row = conn.execute(
            "SELECT cancel_requested, status FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return bool(row and (row["cancel_requested"] or row["status"] == "cancelled"))


def _job_to_dict(row: sqlite3.Row) -> dict:
    job = dict(row)
    job["cancel_requested"] = bool(job["cancel_requested"])
    try:
        job["payload"] = json.loads(job.get("payload") or "{}")
    except json.JSONDecodeError:
        job["payload"] = {}
    if job.get("result"):
        try:
            job["result"] = json.loads(job["result"])
        except json.JSONDecodeError:
            pass
    return job
