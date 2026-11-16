from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class MediaError(Exception):
    """Raised when a media file cannot be inspected or processed."""


def parse_fps(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).strip()
    if not text:
        return None
    if "/" in text:
        numerator, _, denominator = text.partition("/")
        try:
            num = float(numerator)
            den = float(denominator)
        except ValueError:
            return None
        if den == 0 or num <= 0:
            return None
        return num / den
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _to_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _to_float(value: object) -> float | None:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed


def probe_media(path: Path | str, timeout: float = 30.0) -> dict:
    """Read real media metadata with ffprobe. Raises MediaError on failure."""
    media_path = Path(path)
    if not media_path.exists():
        raise MediaError(f"File not found: {media_path}")
    if not media_path.is_file():
        raise MediaError(f"Not a file: {media_path}")
    if media_path.stat().st_size == 0:
        raise MediaError("The file is empty (0 bytes).")

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise MediaError("ffprobe is unavailable; cannot inspect media metadata.")

    cmd = [
        ffprobe,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(media_path),
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaError(
            f"ffprobe timed out after {timeout:.0f}s while reading '{media_path.name}'."
        ) from exc
    except OSError as exc:
        raise MediaError(f"Could not run ffprobe: {exc}") from exc

    if proc.returncode != 0:
        detail = (proc.stderr or "").strip().splitlines()
        hint = detail[-1] if detail else "ffprobe failed"
        raise MediaError(
            f"FFmpeg could not read this file, so it is not a supported video ({hint[:200]})."
        )

    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise MediaError("ffprobe returned unreadable output.") from exc

    streams = data.get("streams") or []
    if not streams:
        raise MediaError(
            "FFmpeg could not read this file, so it is not a supported video "
            "(no media streams found)."
        )

    fmt = data.get("format") or {}

    duration = _to_float(fmt.get("duration"))
    if duration is None:
        for stream in streams:
            stream_duration = _to_float(stream.get("duration"))
            if stream_duration is not None and (duration is None or stream_duration > duration):
                duration = stream_duration

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    video = None
    if video_stream is not None:
        video = {
            "codec_name": video_stream.get("codec_name"),
            "profile": video_stream.get("profile"),
            "width": _to_int(video_stream.get("width")),
            "height": _to_int(video_stream.get("height")),
            "fps": parse_fps(video_stream.get("avg_frame_rate"))
            or parse_fps(video_stream.get("r_frame_rate")),
            "pix_fmt": video_stream.get("pix_fmt"),
            "bit_rate": _to_int(video_stream.get("bit_rate")),
        }

    audio = None
    if audio_stream is not None:
        audio = {
            "codec_name": audio_stream.get("codec_name"),
            "sample_rate": _to_int(audio_stream.get("sample_rate")),
            "channels": _to_int(audio_stream.get("channels")),
            "channel_layout": audio_stream.get("channel_layout"),
            "bit_rate": _to_int(audio_stream.get("bit_rate")),
        }

    return {
        "duration_seconds": duration,
        "format_name": fmt.get("format_name"),
        "file_size_bytes": media_path.stat().st_size,
        "bit_rate": _to_int(fmt.get("bit_rate")),
        "video": video,
        "audio": audio,
    }


def flatten_probe(probe: dict) -> dict:
    """Flatten a probe_media() result into project-metadata keys."""
    video = probe.get("video") or {}
    audio = probe.get("audio") or {}
    return {
        "duration_seconds": probe.get("duration_seconds"),
        "format_name": probe.get("format_name"),
        "file_size_bytes": probe.get("file_size_bytes"),
        "bit_rate": probe.get("bit_rate"),
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": video.get("fps"),
        "pix_fmt": video.get("pix_fmt"),
        "video": video.get("codec_name"),
        "audio": audio.get("codec_name"),
        "audio_sample_rate": audio.get("sample_rate"),
        "audio_channels": audio.get("channels"),
    }


def generate_thumbnail(
    source: Path | str,
    dest: Path | str,
    *,
    at_seconds: float | None = None,
    width: int = 640,
    timeout: float = 60.0,
) -> Path:
    """Extract a single lightweight JPEG frame with FFmpeg."""
    source_path = Path(source)
    dest_path = Path(dest)
    if not source_path.exists():
        raise MediaError(f"File not found: {source_path}")
    if not source_path.is_file():
        raise MediaError(f"Not a file: {source_path}")
    if source_path.stat().st_size == 0:
        raise MediaError("The file is empty (0 bytes).")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise MediaError("ffmpeg is unavailable; cannot generate a thumbnail.")

    if at_seconds is None:
        probe = probe_media(source_path, timeout=min(timeout, 30.0))
        if probe.get("video") is None:
            raise MediaError(f"'{source_path.name}' has no video stream.")
        duration = probe.get("duration_seconds") or 0.0
        at_seconds = max(0.0, duration * 0.5)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{max(0.0, at_seconds):.3f}",
        "-i", str(source_path),
        "-frames:v", "1",
        "-vf", f"scale={max(16, int(width))}:-2",
        "-q:v", "3",
        str(dest_path),
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        dest_path.unlink(missing_ok=True)
        raise MediaError(
            f"thumbnail generation timed out after {timeout:.0f}s on '{source_path.name}'."
        ) from exc
    except OSError as exc:
        raise MediaError(f"Could not run ffmpeg: {exc}") from exc

    if proc.returncode != 0 or not dest_path.is_file() or dest_path.stat().st_size == 0:
        dest_path.unlink(missing_ok=True)
        detail = (proc.stderr or "").strip().splitlines()
        hint = detail[-1] if detail else "ffmpeg produced no frame"
        raise MediaError(f"thumbnail generation failed ({hint[:200]}).")

    return dest_path
