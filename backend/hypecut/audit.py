from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

EXPECTED_REMOTE = "https://github.com/Kanishk3105/HypeCut.git"
MIN_DISK_GB = 20.0
MIN_FFMPEG_MAJOR = 4
PYTHON_MIN = (3, 11)
PYTHON_MAX_EXCLUSIVE = (3, 14)

REQUIRED_WORKSPACE_FILES = (
    "HYPECUT_MASTER_PROMPT.md",
    ".gitignore",
    "docs/DEVELOPMENT_PROGRESS.md",
)

Runner = Callable[[list[str], float], tuple[int, str]]
Which = Callable[[str], str | None]


def default_runner(args: list[str], timeout: float = 15.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return -1, ""
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output


def parse_version_token(text: str) -> tuple[int, ...] | None:
    token = text.strip().lstrip("vV")
    parts: list[int] = []
    for chunk in token.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            break
        parts.append(int(digits))
    if not parts:
        return None
    return tuple(parts)


_VERSION_WORD_RE = re.compile(r"\bversion\s+[^0-9vn]*([vn]?\d+(?:\.\d+)*)", re.IGNORECASE)
_BARE_VERSION_RE = re.compile(r"^\s*(v?\d+(?:\.\d+)+)\s*$", re.MULTILINE)


def parse_tool_version(output: str) -> str | None:
    match = _VERSION_WORD_RE.search(output)
    if match:
        return match.group(1)
    match = _BARE_VERSION_RE.search(output)
    if match:
        return match.group(1)
    return None


def check_python_version(info: tuple[int, int]) -> CheckResult:
    in_range = PYTHON_MIN <= (info[0], info[1]) < PYTHON_MAX_EXCLUSIVE
    detail = f"running Python {info[0]}.{info[1]}, required {'>=' + str(PYTHON_MIN[0]) + '.' + str(PYTHON_MIN[1]) + ' and <' + str(PYTHON_MAX_EXCLUSIVE[0]) + '.' + str(PYTHON_MAX_EXCLUSIVE[1])}"
    return CheckResult("python-runtime", passed=in_range, required=True, detail=detail)


@dataclass
class CheckResult:
    name: str
    passed: bool
    required: bool
    detail: str


@dataclass
class AuditReport:
    generated_at: str
    root: str
    system: dict[str, str]
    checks: list[CheckResult]

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks if c.required)

    @property
    def failed_required(self) -> list[CheckResult]:
        return [c for c in self.checks if c.required and not c.passed]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["ok"] = self.ok
        data["failed_required"] = [c.name for c in self.failed_required]
        return data


def _check_tool(
    label: str,
    executable: str,
    args: list[str],
    which: Which,
    runner: Runner,
    min_version: tuple[int, ...] | None = None,
    required: bool = True,
) -> CheckResult:
    path = which(executable)
    if not path:
        return CheckResult(label, passed=False, required=required, detail=f"{executable} not found on PATH")
    code, output = runner([path, *args], 15.0)
    if code != 0:
        return CheckResult(label, passed=False, required=required, detail=f"{executable} exited with code {code}")
    version = parse_tool_version(output)
    if version is None:
        return CheckResult(label, passed=False, required=required, detail=f"{executable} version could not be parsed")
    parsed = parse_version_token(version)
    if min_version is not None and parsed is not None and parsed < min_version:
        return CheckResult(
            label,
            passed=False,
            required=required,
                detail=f"{executable} {version} is older than required {'.'.join(str(p) for p in min_version)}",
        )
    return CheckResult(label, passed=True, required=required, detail=f"{executable} {version} at {path}")


def _check_disk(root: Path, free_bytes: int) -> CheckResult:
    free_gb = free_bytes / (1024**3)
    passed = free_gb >= MIN_DISK_GB
    return CheckResult(
        "disk-free",
        passed=passed,
        required=True,
        detail=f"{free_gb:.1f} GB free (minimum {MIN_DISK_GB:.0f} GB)",
    )


def _check_workspace(root: Path, runner: Runner) -> list[CheckResult]:
    results: list[CheckResult] = []
    for rel in REQUIRED_WORKSPACE_FILES:
        exists = (root / rel).is_file()
        results.append(
            CheckResult(
                f"workspace-file:{rel}",
                passed=exists,
                required=True,
                detail="present" if exists else "missing",
            )
        )

    code, inside = runner(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"], 15.0)
    is_repo = code == 0 and inside.strip() == "true"
    results.append(
        CheckResult(
            "workspace-git-repo",
            passed=is_repo,
            required=True,
            detail="git repository detected" if is_repo else "not a git repository",
        )
    )

    if is_repo:
        code, url = runner(["git", "-C", str(root), "remote", "get-url", "origin"], 15.0)
        actual = url.strip()
        matches = code == 0 and actual.rstrip(".git").lower() == EXPECTED_REMOTE.rstrip(".git").lower()
        results.append(
            CheckResult(
                "workspace-origin-remote",
                passed=matches,
                required=True,
                detail=f"origin={actual or '<none>'}",
            )
        )
    else:
        results.append(
            CheckResult("workspace-origin-remote", passed=False, required=True, detail="skipped: not a git repository")
        )
    return results


def total_ram_bytes() -> int | None:
    if os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return int(stat.ullTotalPhys)
        except Exception:
            return None
        return None
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        return None


def run_audit(
    root: Path | None = None,
    which: Which | None = None,
    runner: Runner | None = None,
    free_bytes: int | None = None,
) -> AuditReport:
    root = (root or Path(__file__).resolve().parents[2]).resolve()
    which = which or shutil.which
    runner = runner or default_runner

    checks: list[CheckResult] = [check_python_version((sys.version_info[0], sys.version_info[1]))]
    checks.append(_check_tool("tool:git", "git", ["--version"], which, runner))
    checks.append(_check_tool("tool:node", "node", ["--version"], which, runner))
    checks.append(
        _check_tool("tool:ffmpeg", "ffmpeg", ["-version"], which, runner, min_version=(MIN_FFMPEG_MAJOR,))
    )
    checks.append(_check_tool("tool:ffprobe", "ffprobe", ["-version"], which, runner, min_version=(MIN_FFMPEG_MAJOR,)))

    if free_bytes is None:
        try:
            free_bytes = shutil.disk_usage(root).free
        except OSError:
            free_bytes = 0
    checks.append(_check_disk(root, free_bytes))
    checks.extend(_check_workspace(root, runner))

    ram = total_ram_bytes()
    system = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": str(os.cpu_count() or 0),
        "ram_gb": f"{ram / (1024**3):.1f}" if ram else "unknown",
        "root": str(root),
    }
    return AuditReport(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        root=str(root),
        system=system,
        checks=checks,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HypeCut workspace and environment audit")
    parser.add_argument("--root", type=Path, default=None, help="repository root to audit")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    args = parser.parse_args(argv)

    report = run_audit(root=args.root)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"HypeCut environment audit — {'OK' if report.ok else 'FAILED'}")
        for check in report.checks:
            marker = "PASS" if check.passed else ("FAIL" if check.required else "WARN")
            print(f"  [{marker}] {check.name}: {check.detail}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
