from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hypecut import db as dbmod
from hypecut.api import create_app
from hypecut.jobs import JobQueue


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    conn = dbmod.connect(tmp_path / "api.db")
    dbmod.init_db(conn)
    queue = JobQueue(conn, poll_interval=0.01)

    fake_report = {"cpu": {"name": "Fake CPU"}, "ffmpeg": {"found": True}}
    monkeypatch.setattr("hypecut.api.collect_hardware", lambda: dict(fake_report))

    app = create_app(conn=conn, queue=queue)
    with TestClient(app) as test_client:
        test_client.queue = queue  # type: ignore[attr-defined]
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_project_crud(client: TestClient) -> None:
    created = client.post(
        "/api/projects",
        json={"name": "Stream VOD", "source_type": "youtube", "source_ref": "https://youtu.be/dQw4w9WgXcQ"},
    )
    assert created.status_code == 201
    project = created.json()
    pid = project["id"]

    listed = client.get("/api/projects").json()
    assert len(listed) == 1 and listed[0]["id"] == pid

    fetched = client.get(f"/api/projects/{pid}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Stream VOD"

    patched = client.patch(f"/api/projects/{pid}", json={"status": "ingested"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "ingested"

    deleted = client.delete(f"/api/projects/{pid}")
    assert deleted.status_code == 204
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_project_validation(client: TestClient) -> None:
    bad = client.post("/api/projects", json={"name": "", "source_type": "youtube", "source_ref": "x"})
    assert bad.status_code == 422
    bad_type = client.post(
        "/api/projects", json={"name": "x", "source_type": "ftp", "source_ref": "y"}
    )
    assert bad_type.status_code == 422
    assert client.get("/api/projects/missing").status_code == 404


def test_job_lifecycle_via_api(client: TestClient) -> None:
    queue: JobQueue = client.queue  # type: ignore[attr-defined]

    def handler(ctx, payload):
        ctx.report("validation", 50, "working")
        return {"done": True}

    queue.register("api_echo", handler)

    unknown = client.post("/api/jobs", json={"type": "not_registered"})
    assert unknown.status_code == 400

    created = client.post("/api/jobs", json={"type": "api_echo", "payload": {"a": 1}})
    assert created.status_code == 201
    job_id = created.json()["id"]

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.02)
    assert job["status"] == "succeeded"
    assert job["progress"] == 100
    assert job["result"] == {"done": True}

    listed = client.get("/api/jobs", params={"status": "succeeded"}).json()
    assert any(j["id"] == job_id for j in listed)
    assert client.get("/api/jobs/missing").status_code == 404


def test_cancel_and_retry_via_api(client: TestClient) -> None:
    queue: JobQueue = client.queue  # type: ignore[attr-defined]
    queue.stop()

    queue.register("noop2", lambda ctx, payload: None)
    created = client.post("/api/jobs", json={"type": "noop2"})
    job_id = created.json()["id"]

    cancelled = client.post(f"/api/jobs/{job_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    retried = client.post(f"/api/jobs/{job_id}/retry")
    assert retried.status_code == 200
    assert retried.json()["status"] == "queued"

    conflict = client.post(f"/api/jobs/{job_id}/retry")
    assert conflict.status_code == 409

    assert client.post("/api/jobs/missing/cancel").status_code == 404
    assert client.post("/api/jobs/missing/retry").status_code == 404


def test_hardware_endpoint_uses_cache(client: TestClient) -> None:
    first = client.get("/api/hardware")
    assert first.status_code == 200
    body = first.json()
    assert body["cpu"]["name"] == "Fake CPU"
    assert "cached_at" in body

    second = client.get("/api/hardware")
    assert second.json() == body

    refreshed = client.get("/api/hardware", params={"refresh": True})
    assert refreshed.status_code == 200
    assert refreshed.json()["cpu"]["name"] == "Fake CPU"


def test_loopback_only_binding_guard() -> None:
    from hypecut.main import main

    with pytest.raises(SystemExit):
        main(["--host", "0.0.0.0"])
