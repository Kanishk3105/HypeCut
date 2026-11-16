from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from hypecut import db as dbmod
from hypecut.jobs import JobCancelled, JobQueue, STAGES


def make_queue(tmp_path: Path) -> JobQueue:
    conn = dbmod.connect(tmp_path / "jobs.db")
    dbmod.init_db(conn)
    return JobQueue(conn, poll_interval=0.01)


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_enqueue_requires_handler(tmp_path: Path) -> None:
    queue = make_queue(tmp_path)
    with pytest.raises(ValueError, match="no handler"):
        queue.enqueue("unknown_type")


def test_successful_job_lifecycle(tmp_path: Path) -> None:
    queue = make_queue(tmp_path)

    def handler(ctx, payload):
        ctx.report("validation", 10, "starting")
        ctx.report("rendering", 50, "halfway")
        return {"echo": payload.get("value")}

    queue.register("echo", handler)
    queue.start()
    try:
        job = queue.enqueue("echo", payload={"value": 7})
        assert queue.wait_idle(timeout=5.0)
        done = queue.get(job["id"])
        assert done["status"] == "succeeded"
        assert done["progress"] == 100
        assert done["stage"] == "rendering"
        assert done["attempts"] == 1
        assert done["result"] == {"echo": 7}
        assert done["error"] is None
    finally:
        queue.stop()


def test_failing_job_records_error_and_can_retry(tmp_path: Path) -> None:
    queue = make_queue(tmp_path)
    calls = {"n": 0}

    def flaky(ctx, payload):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return {"ok": True}

    queue.register("flaky", flaky)
    queue.start()
    try:
        job = queue.enqueue("flaky")
        assert queue.wait_idle(timeout=5.0)
        failed = queue.get(job["id"])
        assert failed["status"] == "failed"
        assert "boom" in failed["error"]

        retried = queue.retry(job["id"])
        assert retried["status"] == "queued"
        assert queue.wait_idle(timeout=5.0)
        done = queue.get(job["id"])
        assert done["status"] == "succeeded"
        assert done["attempts"] == 2
    finally:
        queue.stop()


def test_retry_rejects_succeeded_job(tmp_path: Path) -> None:
    queue = make_queue(tmp_path)
    queue.register("ok", lambda ctx, payload: None)
    queue.start()
    try:
        job = queue.enqueue("ok")
        assert queue.wait_idle(timeout=5.0)
        with pytest.raises(ValueError, match="failed or cancelled"):
            queue.retry(job["id"])
    finally:
        queue.stop()


def test_cancel_queued_job(tmp_path: Path) -> None:
    queue = make_queue(tmp_path)
    queue.register("noop", lambda ctx, payload: None)
    job = queue.enqueue("noop")
    cancelled = queue.cancel(job["id"])
    assert cancelled["status"] == "cancelled"
    assert queue.get(job["id"])["status"] == "cancelled"


def test_cancel_running_job_cooperatively(tmp_path: Path) -> None:
    queue = make_queue(tmp_path)
    release = threading.Event()
    started = threading.Event()

    def blocking(ctx, payload):
        started.set()
        while True:
            ctx.check_cancelled()
            if release.is_set():
                return None
            time.sleep(0.01)

    queue.register("blocking", blocking)
    queue.start()
    try:
        job = queue.enqueue("blocking")
        assert started.wait(timeout=5.0)
        queue.cancel(job["id"])
        assert wait_for(lambda: queue.get(job["id"])["status"] == "cancelled", timeout=5.0)
        assert queue.get(job["id"])["message"] == "cancelled by user"
    finally:
        release.set()
        queue.stop()


def test_recover_interrupted_jobs(tmp_path: Path) -> None:
    queue = make_queue(tmp_path)
    conn = queue._conn
    now = dbmod.utcnow()
    conn.execute(
        "INSERT INTO jobs (id, type, status, stage, payload, created_at, updated_at) "
        "VALUES ('stuck1', 'x', 'running', 'transcription', '{}', ?, ?)",
        (now, now),
    )
    conn.execute(
        "INSERT INTO jobs (id, type, status, stage, payload, created_at, updated_at) "
        "VALUES ('stuck2', 'x', 'cancel_requested', 'rendering', '{}', ?, ?)",
        (now, now),
    )
    conn.commit()
    requeued = queue.recover_interrupted()
    assert requeued == 2
    assert queue.get("stuck1")["status"] == "queued"
    assert queue.get("stuck2")["status"] == "queued"


def test_single_lane_serializes_jobs(tmp_path: Path) -> None:
    queue = make_queue(tmp_path)
    concurrent = {"now": 0, "max": 0}
    lock = threading.Lock()

    def slow(ctx, payload):
        with lock:
            concurrent["now"] += 1
            concurrent["max"] = max(concurrent["max"], concurrent["now"])
        time.sleep(0.05)
        with lock:
            concurrent["now"] -= 1
        return None

    queue.register("slow", slow)
    queue.start()
    try:
        for _ in range(3):
            queue.enqueue("slow")
        assert queue.wait_idle(timeout=5.0)
        assert concurrent["max"] == 1
    finally:
        queue.stop()


def test_progress_validation(tmp_path: Path) -> None:
    queue = make_queue(tmp_path)
    queue.register("noop", lambda ctx, payload: None)
    job = queue.enqueue("noop")
    from hypecut.jobs import JobContext

    job_ctx = JobContext(job_id=job["id"], _conn=queue._conn, _queue=queue)
    with pytest.raises(ValueError, match="unknown stage"):
        job_ctx.report("not-a-stage", 0, "x")
    with pytest.raises(ValueError, match="between 0 and 100"):
        job_ctx.report("validation", 150, "x")
    job_ctx.report("validation", 42, "half")
    assert queue.get(job["id"])["progress"] == 42
    assert queue.get(job["id"])["stage"] == "validation"


def test_stages_match_spec_order() -> None:
    assert STAGES[0] == "validation"
    assert STAGES[-1] == "export_verification"
    assert len(STAGES) == 14


def test_job_context_cancel_raises(tmp_path: Path) -> None:
    queue = make_queue(tmp_path)
    queue.register("noop", lambda ctx, payload: None)
    job = queue.enqueue("noop")
    queue.cancel(job["id"])
    from hypecut.jobs import JobContext

    ctx = JobContext(job_id=job["id"], _conn=queue._conn, _queue=queue)
    with pytest.raises(JobCancelled):
        ctx.check_cancelled()
