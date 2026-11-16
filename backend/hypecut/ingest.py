from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import db as dbmod
from .jobs import JobContext, JobCancelled

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
ALLOWED_LOCAL_SUFFIXES = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".m4v", ".wmv",
    ".ts", ".mpg", ".mpeg", ".m2ts", ".3gp", ".ogv", ".vob",
}


class IngestError(Exception):
    """User-facing ingestion error with a human-readable message."""


@dataclass(frozen=True)
class VideoRef:
    video_id: str
    url: str
    original: str


def parse_youtube_url(url: str) -> VideoRef | None:
    if not isinstance(url, str):
        return None
    raw = url.strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        return None
    host = (parsed.hostname or "").lower()
    for prefix in ("www.", "m.", "music."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    video_id: str | None = None
    if host == "youtu.be":
        segment = parsed.path.lstrip("/").split("/")[0]
        video_id = segment or None
    elif host == "youtube.com":
        path = parsed.path
        if path.startswith("/watch"):
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        else:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
                video_id = parts[1]
    if not video_id or not VIDEO_ID_RE.match(video_id):
        return None
    return VideoRef(video_id=video_id, url=f"https://www.youtube.com/watch?v={video_id}", original=raw)


def map_error(exc: BaseException) -> str:
    message = str(exc).lower()
    if "private video" in message:
        return "This video is private, so it cannot be fetched."
    if "confirm your age" in message or "age-restricted" in message:
        return "This video is age-restricted and cannot be fetched without sign-in."
    if "not a bot" in message or "sign in to confirm" in message or "blocked" in message:
        return "YouTube blocked this request from this network. Try again later."
    if "not available in your country" in message or "geo restrict" in message:
        return "This video is not available in this region."
    if "unavailable" in message or "removed" in message or "has been terminated" in message:
        return "This video is unavailable (removed, deleted or terminated)."
    if "unsupported url" in message:
        return "This URL is not a supported YouTube video link."
    if "timeout" in message or "timed out" in message or "network" in message or "connection" in message:
        return "Network error while contacting YouTube. Check connectivity and retry."
    return f"Could not retrieve video information: {exc}"


def fetch_info(video_id: str, timeout: float = 20.0) -> dict:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, ExtractorError

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": timeout,
    }
    try:
        with YoutubeDL(opts) as ydl:
            return ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    except (DownloadError, ExtractorError, OSError) as exc:
        raise IngestError(map_error(exc)) from exc


def map_metadata(info: dict, video_id: str) -> dict:
    formats = info.get("formats") or []
    heights = sorted(
        {
            int(f["height"])
            for f in formats
            if f.get("height") and f.get("vcodec") not in (None, "none")
        },
        reverse=True,
    )
    return {
        "video_id": video_id,
        "title": info.get("title"),
        "channel": info.get("channel"),
        "duration_seconds": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "webpage_url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}",
        "qualities": [{"height": h, "label": f"{h}p"} for h in heights],
        "has_heatmap": bool(info.get("heatmap")),
        "format_count": len(formats),
    }


def workspace_dir(project_id: str) -> Path:
    from .db import default_data_dir

    path = default_data_dir() / "workspace" / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def probe_media_file(path: Path, timeout: float = 20.0) -> dict:
    if not path.exists():
        raise IngestError(f"File not found: {path}")
    if not path.is_file():
        raise IngestError(f"Not a file: {path}")
    if path.stat().st_size == 0:
        raise IngestError("The file is empty (0 bytes).")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        if path.suffix.lower() not in ALLOWED_LOCAL_SUFFIXES:
            raise IngestError(
                f"ffprobe is unavailable and '{path.suffix}' is not a known video format."
            )
        return {"duration_seconds": None, "format_name": None, "video": None, "audio": None}
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration,format_name:stream=codec_type,codec_name",
        "-of", "json",
        str(path),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace"
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IngestError(f"Could not inspect the file: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip().splitlines()
        hint = detail[-1] if detail else "ffprobe failed"
        raise IngestError(
            f"FFmpeg could not read this file, so it is not a supported video ({hint[:200]})."
        )
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise IngestError("ffprobe returned unreadable output.") from exc
    streams = data.get("streams") or []
    fmt = data.get("format") or {}
    duration = fmt.get("duration")
    try:
        duration_seconds = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_seconds = None
    return {
        "duration_seconds": duration_seconds,
        "format_name": fmt.get("format_name"),
        "video": next((s.get("codec_name") for s in streams if s.get("codec_type") == "video"), None),
        "audio": next((s.get("codec_name") for s in streams if s.get("codec_type") == "audio"), None),
    }


def _require_project(ctx: JobContext, payload: dict) -> dict:
    project_id = payload.get("project_id")
    if not project_id:
        raise IngestError("payload is missing project_id")
    project = dbmod.get_project(ctx.conn, project_id)
    if project is None:
        raise IngestError("project not found")
    return project


def youtube_metadata_handler(ctx: JobContext, payload: dict) -> dict:
    project = _require_project(ctx, payload)
    if project["source_type"] != "youtube":
        raise IngestError("project is not a YouTube source")
    ref = parse_youtube_url(project["source_ref"])
    if ref is None:
        raise IngestError("project source is not a valid YouTube video URL")
    ctx.report("metadata", 10, "retrieving video metadata")
    info = fetch_info(ref.video_id)
    meta = map_metadata(info, ref.video_id)
    dbmod.set_project_metadata(ctx.conn, project["id"], meta)
    dbmod.update_project(ctx.conn, project["id"], status="metadata_ready")
    ctx.report("metadata", 100, "metadata retrieved")
    return meta


def youtube_download_handler(ctx: JobContext, payload: dict) -> dict:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, ExtractorError

    project = _require_project(ctx, payload)
    if project["source_type"] != "youtube":
        raise IngestError("project is not a YouTube source")
    ref = parse_youtube_url(project["source_ref"])
    if ref is None:
        raise IngestError("project source is not a valid YouTube video URL")
    max_height = payload.get("max_height")
    if max_height is not None:
        try:
            max_height = int(max_height)
        except (TypeError, ValueError) as exc:
            raise IngestError("max_height must be an integer") from exc

    workspace = workspace_dir(project["id"])
    if max_height:
        fmt = (
            f"bestvideo[height<=?{max_height}]+bestaudio/"
            f"best[height<=?{max_height}]/best"
        )
    else:
        fmt = "bestvideo+bestaudio/best"

    def hook(d: dict) -> None:
        ctx.check_cancelled()
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes")
            if total and done is not None:
                percent = min(100.0, max(0.0, done * 100.0 / total))
                speed = d.get("speed")
                message = f"{done / 1e6:.1f} / {total / 1e6:.1f} MB"
                if speed:
                    message += f" · {speed / 1e6:.1f} MB/s"
                ctx.report("download", round(percent, 1), message)
        elif d.get("status") == "finished":
            ctx.report("download", 100, "download finished, finalizing file")

    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30.0,
        "format": fmt,
        "outtmpl": str(workspace / "source.%(ext)s"),
        "progress_hooks": [hook],
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(ref.url, download=True)
    except JobCancelled:
        raise
    except (DownloadError, ExtractorError, OSError) as exc:
        raise IngestError(map_error(exc)) from exc

    ctx.check_cancelled()

    source_path: str | None = None
    for entry in info.get("requested_downloads") or []:
        candidate = entry.get("filepath")
        if candidate and Path(candidate).is_file():
            source_path = candidate
            break
    if source_path is None:
        candidates = sorted(workspace.glob("source.*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            source_path = str(candidates[0])
    if not source_path:
        raise IngestError("Download reported success but no file was found in the workspace.")

    probe = probe_media_file(Path(source_path))
    meta = dict(project.get("metadata") or {})
    meta.update(
        {
            "source_path": source_path,
            "downloaded_format": info.get("format_id"),
            "downloaded_height": info.get("height"),
            "duration_seconds": probe.get("duration_seconds") or info.get("duration"),
            "format_name": probe.get("format_name"),
        }
    )
    dbmod.set_project_metadata(ctx.conn, project["id"], meta)
    dbmod.update_project(ctx.conn, project["id"], status="downloaded")
    return meta


def local_import_handler(ctx: JobContext, payload: dict) -> dict:
    project = _require_project(ctx, payload)
    if project["source_type"] != "local":
        raise IngestError("project is not a local file source")
    path = Path(project["source_ref"])
    ctx.report("validation", 30, "inspecting media file")
    probe = probe_media_file(path)
    meta = dict(project.get("metadata") or {})
    meta.update(
        {
            "source_path": str(path),
            "file_name": path.name,
            "file_size_bytes": path.stat().st_size,
            **{k: v for k, v in probe.items() if k in ("duration_seconds", "format_name", "video", "audio")},
        }
    )
    dbmod.set_project_metadata(ctx.conn, project["id"], meta)
    dbmod.update_project(ctx.conn, project["id"], status="imported")
    ctx.report("validation", 100, "file imported")
    return meta
