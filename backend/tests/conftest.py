from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def _ensure_toolchain_on_path() -> None:
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links",
        Path("C:/ffmpeg/bin"),
        Path("C:/ProgramData/chocolatey/bin"),
    ]
    existing = [str(c) for c in candidates if c.is_dir()]
    if existing:
        os.environ["PATH"] = os.pathsep.join(existing) + os.pathsep + os.environ.get("PATH", "")


def _isolate_data_dir() -> None:
    # Keep test-generated workspaces/thumbnails out of the real data directory.
    os.environ.setdefault(
        "HYPECUT_DATA_DIR",
        str(Path(tempfile.gettempdir()) / "hypecut-test-data"),
    )


_ensure_toolchain_on_path()
_isolate_data_dir()
