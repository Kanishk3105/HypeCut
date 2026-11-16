from __future__ import annotations

import json
import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import __version__, db as dbmod
from .hardware import collect_hardware
from .ingest import (
    local_import_handler,
    youtube_download_handler,
    youtube_metadata_handler,
    workspace_dir,
)
from .jobs import JobContext, JobQueue

logger = logging.getLogger("hypecut.api")


def _hardware_probe_handler(ctx: JobContext, payload: dict) -> dict:
    ctx.report("validation", None, "collecting hardware diagnostics")
    report = collect_hardware()
    ctx.report("validation", 100, "diagnostics complete")
    return report


def register_default_handlers(queue: JobQueue) -> None:
    if not queue.has("hardware_probe"):
        queue.register("hardware_probe", _hardware_probe_handler)
    if not queue.has("youtube_metadata"):
        queue.register("youtube_metadata", youtube_metadata_handler)
    if not queue.has("youtube_download"):
        queue.register("youtube_download", youtube_download_handler)
    if not queue.has("local_import"):
        queue.register("local_import", local_import_handler)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: Literal["youtube", "local"]
    source_ref: str = Field(min_length=1, max_length=2000)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, min_length=1, max_length=50)


class JobCreate(BaseModel):
    type: str = Field(min_length=1, max_length=100)
    project_id: str | None = None
    payload: dict = Field(default_factory=dict)


class DownloadRequest(BaseModel):
    max_height: int | None = Field(default=None, ge=144, le=4320)


def create_app(conn=None, queue: JobQueue | None = None) -> FastAPI:
    if conn is None:
        conn = dbmod.connect()
    dbmod.init_db(conn)
    if queue is None:
        queue = JobQueue(conn)
    register_default_handlers(queue)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        queue.start()
        logger.info("job queue started")
        yield
        queue.stop()
        logger.info("job queue stopped")

    app = FastAPI(title="HypeCut Local API", version=__version__, lifespan=lifespan)
    app.state.conn = conn
    app.state.queue = queue

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/api/projects")
    def list_projects() -> list[dict]:
        return dbmod.list_projects(conn)

    @app.post("/api/projects", status_code=201)
    def create_project(body: ProjectCreate) -> dict:
        return dbmod.create_project(conn, body.name, body.source_type, body.source_ref)

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> dict:
        project = dbmod.get_project(conn, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        return project

    @app.patch("/api/projects/{project_id}")
    def update_project(project_id: str, body: ProjectUpdate) -> dict:
        project = dbmod.update_project(
            conn, project_id, name=body.name, status=body.status
        )
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        return project

    @app.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: str) -> None:
        if not dbmod.delete_project(conn, project_id):
            raise HTTPException(status_code=404, detail="project not found")

    @app.post("/api/projects/{project_id}/fetch-metadata", status_code=201)
    def fetch_metadata(project_id: str) -> dict:
        project = dbmod.get_project(conn, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        if project["source_type"] != "youtube":
            raise HTTPException(status_code=409, detail="project is not a YouTube source")
        try:
            return queue.enqueue("youtube_metadata", payload={"project_id": project_id})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/{project_id}/download", status_code=201)
    def download_video(project_id: str, body: DownloadRequest | None = None) -> dict:
        project = dbmod.get_project(conn, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        if project["source_type"] != "youtube":
            raise HTTPException(status_code=409, detail="project is not a YouTube source")
        payload: dict = {"project_id": project_id}
        if body and body.max_height is not None:
            payload["max_height"] = body.max_height
        try:
            return queue.enqueue("youtube_download", payload=payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/{project_id}/import", status_code=201)
    def import_local(project_id: str) -> dict:
        project = dbmod.get_project(conn, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        if project["source_type"] != "local":
            raise HTTPException(status_code=409, detail="project is not a local file source")
        try:
            return queue.enqueue("local_import", payload={"project_id": project_id})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/upload", status_code=201)
    async def upload_local(file: UploadFile = File(...), name: str | None = Query(default=None)) -> dict:
        original = Path(file.filename or "uploaded_video").name
        project = dbmod.create_project(
            conn,
            name=(name or original).strip()[:200] or original,
            source_type="local",
            source_ref="pending",
        )
        workspace = workspace_dir(project["id"])
        destination = workspace / original
        try:
            with destination.open("wb") as out:
                while chunk := await file.read(1024 * 1024):
                    out.write(chunk)
        except OSError as exc:
            dbmod.delete_project(conn, project["id"])
            raise HTTPException(status_code=500, detail=f"could not store upload: {exc}") from exc
        dbmod.update_project(conn, project["id"], source_ref=str(destination))
        try:
            job = queue.enqueue("local_import", payload={"project_id": project["id"]})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"project": dbmod.get_project(conn, project["id"]), "job": job}

    @app.get("/api/projects/{project_id}/thumbnail")
    def project_thumbnail(project_id: str) -> FileResponse:
        project = dbmod.get_project(conn, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        thumb = (project.get("metadata") or {}).get("thumbnail_path")
        if not thumb:
            raise HTTPException(status_code=404, detail="no thumbnail for this project yet")
        try:
            resolved = Path(thumb).resolve()
        except OSError as exc:
            raise HTTPException(status_code=404, detail="thumbnail file missing") from exc
        workspace_root = (dbmod.default_data_dir() / "workspace").resolve()
        if not resolved.is_relative_to(workspace_root) or not resolved.is_file():
            raise HTTPException(status_code=404, detail="thumbnail file missing")
        return FileResponse(resolved, media_type="image/jpeg")

    @app.get("/api/jobs")
    def list_jobs(
        status: str | None = Query(default=None),
        project_id: str | None = Query(default=None),
    ) -> list[dict]:
        return queue.list(status=status, project_id=project_id)

    @app.post("/api/jobs", status_code=201)
    def enqueue_job(body: JobCreate) -> dict:
        try:
            return queue.enqueue(body.type, project_id=body.project_id, payload=body.payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = queue.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str) -> dict:
        job = queue.cancel(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.post("/api/jobs/{job_id}/retry")
    def retry_job(job_id: str) -> dict:
        try:
            job = queue.retry(job_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.get("/api/hardware")
    def get_hardware(refresh: bool = Query(default=False)) -> dict:
        if not refresh:
            cached = dbmod.get_setting(conn, "hardware_report")
            if cached:
                try:
                    return json.loads(cached)
                except json.JSONDecodeError:
                    pass
        report = collect_hardware()
        report["cached_at"] = dbmod.utcnow()
        dbmod.set_setting(conn, "hardware_report", json.dumps(report))
        return report

    return app
