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


def wait_job(client: TestClient, job_id: str, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("succeeded", "failed", "cancelled"):
            return job
        time.sleep(0.02)
    raise AssertionError("job did not finish in time")


def test_metadata_flow_via_api(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "hypecut.ingest.fetch_info",
        lambda video_id, timeout=20.0: {
            "title": "Real Title",
            "channel": "Chan",
            "duration": 42,
            "thumbnail": "https://img.example/a.jpg",
            "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
            "heatmap": [],
            "formats": [{"height": 720, "vcodec": "avc1"}],
        },
    )
    created = client.post(
        "/api/projects",
        json={"name": "YT", "source_type": "youtube", "source_ref": "https://youtu.be/jNQXAC9IVRw"},
    ).json()

    fetched = client.post(f"/api/projects/{created['id']}/fetch-metadata")
    assert fetched.status_code == 201
    job = wait_job(client, fetched.json()["id"])
    assert job["status"] == "succeeded"
    assert job["result"]["title"] == "Real Title"

    project = client.get(f"/api/projects/{created['id']}").json()
    assert project["status"] == "metadata_ready"
    assert project["metadata"]["title"] == "Real Title"
    assert project["metadata"]["qualities"] == [{"height": 720, "label": "720p"}]


def test_fetch_metadata_rejects_wrong_project_type(client: TestClient) -> None:
    local = client.post(
        "/api/projects",
        json={"name": "L", "source_type": "local", "source_ref": "C:/x.mp4"},
    ).json()
    assert client.post(f"/api/projects/{local['id']}/fetch-metadata").status_code == 409
    assert client.post("/api/projects/missing/fetch-metadata").status_code == 404


def test_download_enqueue_does_not_run_without_queue(client: TestClient) -> None:
    queue: JobQueue = client.queue  # type: ignore[attr-defined]
    queue.stop()
    project = client.post(
        "/api/projects",
        json={"name": "YT", "source_type": "youtube", "source_ref": "https://youtu.be/jNQXAC9IVRw"},
    ).json()
    resp = client.post(f"/api/projects/{project['id']}/download", json={"max_height": 720})
    assert resp.status_code == 201
    body = resp.json()
    assert body["type"] == "youtube_download"
    assert body["status"] == "queued"
    assert body["payload"] == {"project_id": project["id"], "max_height": 720}
    assert client.post(f"/api/projects/{project['id']}/download", json={"max_height": 99999}).status_code == 422


def test_local_import_flow_via_api(client: TestClient, tmp_path: Path) -> None:
    import subprocess

    video = tmp_path / "vid.mp4"
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=128x128:rate=10",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    project = client.post(
        "/api/projects",
        json={"name": "Local", "source_type": "local", "source_ref": str(video)},
    ).json()
    resp = client.post(f"/api/projects/{project['id']}/import")
    assert resp.status_code == 201
    job = wait_job(client, resp.json()["id"])
    assert job["status"] == "succeeded", job.get("error")
    updated = client.get(f"/api/projects/{project['id']}").json()
    assert updated["status"] == "imported"
    assert updated["metadata"]["duration_seconds"] == pytest.approx(1.0, abs=0.3)


def test_upload_flow_via_api(client: TestClient, tmp_path: Path) -> None:
    import subprocess

    video = tmp_path / "upload_src.mp4"
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=128x128:rate=10",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    payload = video.read_bytes()
    resp = client.post(
        "/api/projects/upload?name=Uploaded+clip",
        files={"file": ("upload_src.mp4", payload, "video/mp4")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    project = body["project"]
    assert project["name"] == "Uploaded clip"
    assert project["source_type"] == "local"
    assert project["source_ref"].endswith("upload_src.mp4")
    job = wait_job(client, body["job"]["id"])
    assert job["status"] == "succeeded", job.get("error")
    updated = client.get(f"/api/projects/{project['id']}").json()
    assert updated["status"] == "imported"
    assert Path(updated["metadata"]["source_path"]).is_file()
