from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hypecut.media import (
    MediaError,
    flatten_probe,
    generate_thumbnail,
    parse_fps,
    probe_media,
)


def make_video(path: Path, *, size: str = "128x128", rate: str = "10", duration: str = "1") -> Path:
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"testsrc=duration={duration}:size={size}:rate={rate}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return path


def make_audio_only(path: Path) -> Path:
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:a", "aac", str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return path


class TestParseFps:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("30/1", 30.0),
            ("30000/1001", pytest.approx(29.97, abs=0.01)),
            ("0/0", None),
            ("25", 25.0),
            (24, 24.0),
            (0, None),
            (-5, None),
            (None, None),
            ("", None),
            ("abc", None),
            (True, None),
        ],
    )
    def test_parse_fps(self, value, expected) -> None:
        assert parse_fps(value) == expected


def test_probe_media_reads_real_metadata(tmp_path: Path) -> None:
    video = make_video(tmp_path / "clip.mp4")
    probe = probe_media(video)
    assert probe["duration_seconds"] == pytest.approx(1.0, abs=0.3)
    assert probe["format_name"]
    assert probe["file_size_bytes"] == video.stat().st_size > 0
    assert probe["bit_rate"] and probe["bit_rate"] > 0
    assert probe["video"]["codec_name"] == "h264"
    assert probe["video"]["width"] == 128
    assert probe["video"]["height"] == 128
    assert probe["video"]["fps"] == pytest.approx(10.0, abs=0.5)
    assert probe["video"]["pix_fmt"] == "yuv420p"
    assert probe["audio"]["codec_name"] == "aac"
    assert probe["audio"]["sample_rate"] > 0
    assert probe["audio"]["channels"] >= 1


def test_probe_media_audio_only(tmp_path: Path) -> None:
    audio = make_audio_only(tmp_path / "tone.m4a")
    probe = probe_media(audio)
    assert probe["video"] is None
    assert probe["audio"]["codec_name"] == "aac"
    assert probe["duration_seconds"] == pytest.approx(1.0, abs=0.3)


def test_probe_media_missing_file(tmp_path: Path) -> None:
    with pytest.raises(MediaError, match="not found"):
        probe_media(tmp_path / "nope.mp4")


def test_probe_media_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    with pytest.raises(MediaError, match="empty"):
        probe_media(empty)


def test_probe_media_rejects_non_media(tmp_path: Path) -> None:
    text = tmp_path / "notes.txt"
    text.write_text("hello", encoding="utf-8")
    with pytest.raises(MediaError, match="could not read|no media streams"):
        probe_media(text)


def test_flatten_probe_maps_keys() -> None:
    flat = flatten_probe(
        {
            "duration_seconds": 3.5,
            "format_name": "mp4",
            "file_size_bytes": 999,
            "bit_rate": 1234,
            "video": {"codec_name": "h264", "width": 640, "height": 360, "fps": 24.0, "pix_fmt": "yuv420p"},
            "audio": {"codec_name": "opus", "sample_rate": 48000, "channels": 2},
        }
    )
    assert flat == {
        "duration_seconds": 3.5,
        "format_name": "mp4",
        "file_size_bytes": 999,
        "bit_rate": 1234,
        "width": 640,
        "height": 360,
        "fps": 24.0,
        "pix_fmt": "yuv420p",
        "video": "h264",
        "audio": "opus",
        "audio_sample_rate": 48000,
        "audio_channels": 2,
    }


def test_flatten_probe_handles_no_streams() -> None:
    flat = flatten_probe(
        {"duration_seconds": None, "format_name": None, "file_size_bytes": 1, "bit_rate": None, "video": None, "audio": None}
    )
    assert flat["video"] is None
    assert flat["audio"] is None
    assert flat["width"] is None
    assert flat["fps"] is None


def test_generate_thumbnail_writes_jpeg(tmp_path: Path) -> None:
    video = make_video(tmp_path / "clip.mp4")
    dest = tmp_path / "out" / "thumb.jpg"
    result = generate_thumbnail(video, dest)
    assert result == dest
    assert dest.is_file()
    assert dest.read_bytes()[:2] == b"\xff\xd8"

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_streams", str(dest),
        ],
        capture_output=True, text=True, timeout=30, encoding="utf-8",
        check=True,
    )
    import json

    stream = json.loads(probe.stdout)["streams"][0]
    assert stream["width"] == 640
    assert stream["height"] == 640


def test_generate_thumbnail_respects_width(tmp_path: Path) -> None:
    video = make_video(tmp_path / "clip.mp4", size="320x180")
    dest = tmp_path / "thumb.jpg"
    generate_thumbnail(video, dest, width=160, at_seconds=0.0)
    import json

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(dest)],
        capture_output=True, text=True, timeout=30, encoding="utf-8", check=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    assert stream["width"] == 160
    assert stream["height"] == 90  # 180 * (160/320), rounded to even


def test_generate_thumbnail_rejects_audio_only(tmp_path: Path) -> None:
    audio = make_audio_only(tmp_path / "tone.m4a")
    with pytest.raises(MediaError, match="no video stream"):
        generate_thumbnail(audio, tmp_path / "thumb.jpg")


def test_generate_thumbnail_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(MediaError, match="not found"):
        generate_thumbnail(tmp_path / "nope.mp4", tmp_path / "thumb.jpg")


def test_generate_thumbnail_rejects_unseekable_position(tmp_path: Path) -> None:
    video = make_video(tmp_path / "clip.mp4")
    with pytest.raises(MediaError, match="thumbnail generation failed"):
        generate_thumbnail(video, tmp_path / "thumb.jpg", at_seconds=3600.0)


def test_generate_thumbnail_without_ffmpeg(tmp_path: Path, monkeypatch) -> None:
    video = make_video(tmp_path / "clip.mp4")
    monkeypatch.setattr("hypecut.media.shutil.which", lambda name: None)
    with pytest.raises(MediaError, match="ffmpeg is unavailable"):
        generate_thumbnail(video, tmp_path / "thumb.jpg", at_seconds=0.0)
