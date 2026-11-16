from __future__ import annotations

import json
from pathlib import Path

import pytest
from yt_dlp.utils import DownloadError

from hypecut import db as dbmod
from hypecut.ingest import (
    IngestError,
    local_import_handler,
    map_error,
    map_metadata,
    parse_youtube_url,
    probe_media_file,
    youtube_download_handler,
    youtube_metadata_handler,
)
from hypecut.jobs import JobCancelled


class FakeCtx:
    def __init__(self, conn, job_id: str = "job1"):
        self.job_id = job_id
        self.conn = conn
        self.reports: list[tuple[str, float | None, str]] = []

    def report(self, stage: str, progress: float | None = None, message: str = "") -> None:
        self.reports.append((stage, progress, message))

    def check_cancelled(self) -> None:
        return None


VALID_URLS = [
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "https://youtube.com/watch?v=jNQXAC9IVRw",
    "http://m.youtube.com/watch?v=jNQXAC9IVRw&t=42",
    "https://youtu.be/jNQXAC9IVRw",
    "https://www.youtu.be/jNQXAC9IVRw?si=abc",
    "https://www.youtube.com/shorts/jNQXAC9IVRw",
    "https://www.youtube.com/embed/jNQXAC9IVRw",
    "https://www.youtube.com/live/jNQXAC9IVRw",
    "https://www.youtube.com/v/jNQXAC9IVRw",
    "https://music.youtube.com/watch?v=jNQXAC9IVRw&list=PL1",
    "  https://www.youtube.com/watch?v=jNQXAC9IVRw  ",
]

INVALID_URLS = [
    "",
    "   ",
    "not a url",
    "ftp://youtube.com/watch?v=jNQXAC9IVRw",
    "javascript:alert(1)",
    "https://www.youtube.com/watch?v=short",
    "https://www.youtube.com/watch?v=jNQXAC9IVRw12",  # 12 chars
    "https://www.youtube.com/playlist?list=PL123",
    "https://www.youtube.com/results?search_query=cats",
    "https://www.youtube.com/@somechannel",
    "https://youtu.be/",
    "https://vimeo.com/12345",
    "https://www.youtube.com/watch",
    None,
    123,
]


@pytest.mark.parametrize("url", VALID_URLS)
def test_parse_valid_youtube_urls(url) -> None:
    ref = parse_youtube_url(url)
    assert ref is not None
    assert ref.video_id == "jNQXAC9IVRw"
    assert ref.url == "https://www.youtube.com/watch?v=jNQXAC9IVRw"


@pytest.mark.parametrize("url", INVALID_URLS)
def test_parse_invalid_youtube_urls(url) -> None:
    assert parse_youtube_url(url) is None


def test_map_metadata_with_heatmap_and_qualities() -> None:
    info = {
        "title": "Test Stream",
        "channel": "Tester",
        "duration": 3600,
        "thumbnail": "https://img.example/t.jpg",
        "webpage_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "heatmap": [{"start_time": 0, "end_time": 1, "value": 0.5}],
        "formats": [
            {"height": 1080, "vcodec": "avc1", "ext": "mp4"},
            {"height": 720, "vcodec": "avc1", "ext": "mp4"},
            {"height": 720, "vcodec": "avc1", "ext": "webm"},
            {"height": None, "vcodec": "none", "ext": "m4a"},
            {"vcodec": "vp9", "ext": "dash"},
        ],
    }
    meta = map_metadata(info, "jNQXAC9IVRw")
    assert meta["title"] == "Test Stream"
    assert meta["duration_seconds"] == 3600
    assert meta["has_heatmap"] is True
    assert meta["qualities"] == [
        {"height": 1080, "label": "1080p"},
        {"height": 720, "label": "720p"},
    ]
    assert meta["format_count"] == 5


def test_map_metadata_without_heatmap() -> None:
    meta = map_metadata({"title": "x", "formats": []}, "abcdefghijk")
    assert meta["has_heatmap"] is False
    assert meta["qualities"] == []


@pytest.mark.parametrize(
    ("needle", "expected"),
    [
        ("Private video", "private"),
        ("age-restricted", "age-restricted"),
        ("Sign in to confirm", "blocked"),
        ("not available in your country", "region"),
        ("Video unavailable", "unavailable"),
        ("Unsupported URL", "supported YouTube"),
        ("Connection timed out", "Network error"),
        ("something odd", "Could not retrieve"),
    ],
)
def test_map_error_messages(needle: str, expected: str) -> None:
    assert expected.lower() in map_error(DownloadError(needle)).lower()


def test_fetch_info_uses_ytdlp_and_maps_errors(monkeypatch) -> None:
    captured: dict = {}

    class FakeYDL:
        def __init__(self, opts):
            captured.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            assert download is False
            assert "jNQXAC9IVRw" in url
            return {"title": "ok", "formats": []}

    import hypecut.ingest as ingest_mod

    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)
    result = ingest_mod.fetch_info("jNQXAC9IVRw")
    assert result["title"] == "ok"
    assert captured["skip_download"] is True
    assert captured["noplaylist"] is True
    assert captured["socket_timeout"] == 20.0


def test_fetch_info_maps_download_error(monkeypatch) -> None:
    import hypecut.ingest as ingest_mod

    def boom(video_id, timeout=20.0):
        raise IngestError(map_error(DownloadError("Private video")))

    monkeypatch.setattr(ingest_mod, "fetch_info", boom)
    with pytest.raises(IngestError, match="private"):
        ingest_mod.fetch_info("jNQXAC9IVRw")


def make_conn(tmp_path: Path):
    conn = dbmod.connect(tmp_path / "ingest.db")
    dbmod.init_db(conn)
    return conn


def test_youtube_metadata_handler_stores_metadata(tmp_path: Path, monkeypatch) -> None:
    conn = make_conn(tmp_path)
    project = dbmod.create_project(conn, "p", "youtube", "https://youtu.be/jNQXAC9IVRw")
    monkeypatch.setattr(
        "hypecut.ingest.fetch_info",
        lambda video_id, timeout=20.0: {
            "title": "Me at the zoo",
            "channel": "jawed",
            "duration": 19,
            "thumbnail": "https://img.example/x.jpg",
            "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
            "heatmap": [{"start_time": 0}],
            "formats": [{"height": 480, "vcodec": "avc1"}],
        },
    )
    ctx = FakeCtx(conn)
    result = youtube_metadata_handler(ctx, {"project_id": project["id"]})  # type: ignore[arg-type]
    assert result["title"] == "Me at the zoo"
    assert result["has_heatmap"] is True
    stored = dbmod.get_project(conn, project["id"])
    assert stored["metadata"]["title"] == "Me at the zoo"
    assert stored["status"] == "metadata_ready"
    assert ctx.reports[-1] == ("metadata", 100, "metadata retrieved")


def test_youtube_metadata_handler_rejects_local_project(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    project = dbmod.create_project(conn, "p", "local", "C:/x.mp4")
    ctx = FakeCtx(conn)
    with pytest.raises(IngestError, match="not a YouTube"):
        youtube_metadata_handler(ctx, {"project_id": project["id"]})  # type: ignore[arg-type]


def test_youtube_metadata_handler_rejects_bad_url(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    project = dbmod.create_project(conn, "p", "youtube", "https://example.com/not-youtube")
    ctx = FakeCtx(conn)
    with pytest.raises(IngestError, match="not a valid YouTube"):
        youtube_metadata_handler(ctx, {"project_id": project["id"]})  # type: ignore[arg-type]


class FakeYDLDownload:
    last_opts: dict = {}

    def __init__(self, opts):
        FakeYDLDownload.last_opts = opts
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=True):
        hooks = self.opts["progress_hooks"]
        hooks[0]({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100, "speed": 1e6})
        hooks[0]({"status": "finished"})
        outtmpl = self.opts["outtmpl"].replace("%(ext)s", "mp4")
        Path(outtmpl).write_bytes(b"fake-video-bytes")
        return {
            "format_id": "22",
            "height": 720,
            "duration": 5,
            "requested_downloads": [{"filepath": outtmpl}],
        }


def test_youtube_download_handler_success(tmp_path: Path, monkeypatch) -> None:
    conn = make_conn(tmp_path)
    project = dbmod.create_project(conn, "p", "youtube", "https://youtu.be/jNQXAC9IVRw")

    def fake_ws(pid: str) -> Path:
        path = tmp_path / "ws"
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr("hypecut.ingest.workspace_dir", fake_ws)
    monkeypatch.setattr("hypecut.ingest.probe_media_file", lambda path, timeout=20.0: {
        "duration_seconds": 5.0, "format_name": "mp4", "video": "h264", "audio": "aac",
    })
    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDLDownload)
    ctx = FakeCtx(conn)
    result = youtube_download_handler(ctx, {"project_id": project["id"], "max_height": 720})  # type: ignore[arg-type]
    assert result["source_path"].endswith("source.mp4")
    assert result["downloaded_height"] == 720
    stages = [r[0] for r in ctx.reports]
    assert stages == ["download", "download"]
    assert ctx.reports[0][1] == 50.0
    assert "MB/s" in ctx.reports[0][2]
    stored = dbmod.get_project(conn, project["id"])
    assert stored["status"] == "downloaded"
    assert stored["metadata"]["source_path"].endswith("source.mp4")
    opts = FakeYDLDownload.last_opts
    assert "height<=?720" in opts["format"]
    # DASH-only videos have no progressive stream, so the selector must merge
    # video+audio before falling back to a single file.
    assert "bestvideo" in opts["format"] and "bestaudio" in opts["format"]


class FakeYDLDownloadCancelled(FakeYDLDownload):
    def extract_info(self, url, download=True):
        hooks = self.opts["progress_hooks"]
        hooks[0]({"status": "downloading", "downloaded_bytes": 1, "total_bytes": 100})
        raise JobCancelled()


def test_youtube_download_handler_cancellation(tmp_path: Path, monkeypatch) -> None:
    conn = make_conn(tmp_path)
    project = dbmod.create_project(conn, "p", "youtube", "https://youtu.be/jNQXAC9IVRw")
    monkeypatch.setattr("hypecut.ingest.workspace_dir", lambda pid: tmp_path / "ws")
    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDLDownloadCancelled)
    ctx = FakeCtx(conn)
    with pytest.raises(JobCancelled):
        youtube_download_handler(ctx, {"project_id": project["id"]})  # type: ignore[arg-type]


def test_youtube_download_handler_maps_errors(tmp_path: Path, monkeypatch) -> None:
    conn = make_conn(tmp_path)
    project = dbmod.create_project(conn, "p", "youtube", "https://youtu.be/jNQXAC9IVRw")
    monkeypatch.setattr("hypecut.ingest.workspace_dir", lambda pid: tmp_path / "ws")

    class FailingYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=True):
            raise DownloadError("Video unavailable")

    monkeypatch.setattr("yt_dlp.YoutubeDL", FailingYDL)
    ctx = FakeCtx(conn)
    with pytest.raises(IngestError, match="unavailable"):
        youtube_download_handler(ctx, {"project_id": project["id"]})  # type: ignore[arg-type]


def make_synthetic_video(path: Path) -> Path:
    import subprocess

    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=128x128:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return path


def test_probe_media_file_accepts_synthetic_video(tmp_path: Path) -> None:
    video = make_synthetic_video(tmp_path / "clip.mp4")
    result = probe_media_file(video)
    assert result["video"] == "h264"
    assert result["audio"] == "aac"
    assert result["duration_seconds"] == pytest.approx(1.0, abs=0.3)


def test_probe_media_file_rejects_non_video(tmp_path: Path) -> None:
    text = tmp_path / "notes.txt"
    text.write_text("hello", encoding="utf-8")
    with pytest.raises(IngestError, match="could not read|not a supported"):
        probe_media_file(text)


def test_probe_media_file_rejects_missing_and_empty(tmp_path: Path) -> None:
    with pytest.raises(IngestError, match="not found"):
        probe_media_file(tmp_path / "nope.mp4")
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    with pytest.raises(IngestError, match="empty"):
        probe_media_file(empty)


def test_local_import_handler(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    video = make_synthetic_video(tmp_path / "local.mp4")
    project = dbmod.create_project(conn, "p", "local", str(video))
    ctx = FakeCtx(conn)
    result = local_import_handler(ctx, {"project_id": project["id"]})  # type: ignore[arg-type]
    assert result["file_name"] == "local.mp4"
    assert result["duration_seconds"] == pytest.approx(1.0, abs=0.3)
    stored = dbmod.get_project(conn, project["id"])
    assert stored["status"] == "imported"
    assert stored["metadata"]["video"] == "h264"


def test_local_import_handler_rejects_missing_file(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    project = dbmod.create_project(conn, "p", "local", str(tmp_path / "gone.mp4"))
    ctx = FakeCtx(conn)
    with pytest.raises(IngestError, match="not found"):
        local_import_handler(ctx, {"project_id": project["id"]})  # type: ignore[arg-type]


def test_workspace_dir_created(tmp_path: Path, monkeypatch) -> None:
    import hypecut.db as dbmod_mod

    monkeypatch.setattr(dbmod_mod, "default_data_dir", lambda: tmp_path)
    from hypecut.ingest import workspace_dir

    path = workspace_dir("abc123")
    assert path.is_dir()
    assert path == tmp_path / "workspace" / "abc123"
