from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from . import __version__, db as dbmod
from .hardware import collect_hardware
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
