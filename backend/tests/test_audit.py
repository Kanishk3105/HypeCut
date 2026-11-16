from __future__ import annotations

import json
from pathlib import Path

from hypecut.audit import (
    EXPECTED_REMOTE,
    AuditReport,
    CheckResult,
    check_python_version,
    main,
    parse_tool_version,
    parse_version_token,
    run_audit,
)

SAMPLES = [
    ("ffmpeg version 9.0.2-full_build-www.gyan.dev Copyright (c) 2000-2026", "9.0.2"),
    ("ffmpeg version 6.1.1-3ubuntu5 Copyright (c) 2000-2023", "6.1.1"),
    ("ffprobe version n5.1.4 Copyright (c) 2007-2022", "n5.1.4"),
    ("node --version -> v24.14.1", "v24.14.1"),
]


def test_parse_tool_version_samples() -> None:
    for output, expected in SAMPLES:
        assert parse_tool_version(output) == expected


def test_parse_tool_version_missing() -> None:
    assert parse_tool_version("no version here") is None


def test_parse_version_token() -> None:
    assert parse_version_token("v24.14.1") == (24, 14, 1)
    assert parse_version_token("9.0.2-full_build") == (9, 0, 2)
    assert parse_version_token("abc") is None
    assert parse_version_token("") is None


def test_check_python_version_bounds() -> None:
    assert check_python_version((3, 12)).passed is True
    assert check_python_version((3, 11)).passed is True
    assert check_python_version((3, 10)).passed is False
    assert check_python_version((3, 14)).passed is False
    assert check_python_version((3, 10)).required is True


def make_workspace(root: Path, *, with_files: bool = True, remote: str = EXPECTED_REMOTE) -> None:
    if with_files:
        (root / "HYPECUT_MASTER_PROMPT.md").write_text("spec", encoding="utf-8")
        (root / ".gitignore").write_text("node_modules/", encoding="utf-8")
        (root / "docs").mkdir(exist_ok=True)
        (root / "docs" / "DEVELOPMENT_PROGRESS.md").write_text("progress", encoding="utf-8")


def fake_which(found: dict[str, str | None]):
    return lambda name: found.get(name)


def fake_runner(versions: dict[str, str], *, remote: str = EXPECTED_REMOTE, repo: bool = True):
    def run(args: list[str], timeout: float) -> tuple[int, str]:
        joined = " ".join(args)
        if "rev-parse" in joined:
            return (0, "true\n") if repo else (128, "not a git repository\n")
        if "get-url" in joined:
            if remote is None:
                return 1, "No such remote 'origin'\n"
            return 0, remote + "\n"
        exe = Path(args[0]).stem
        if exe in versions:
            return 0, versions[exe] + "\n"
        return 0, ""

    return run


def test_audit_ok(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    report = run_audit(
        root=tmp_path,
        which=fake_which({"git": "C:/git.exe", "node": "C:/node.exe", "ffmpeg": "C:/ffmpeg.exe", "ffprobe": "C:/ffprobe.exe"}),
        runner=fake_runner(
            {
                "git": "git version 2.50.1.windows.1",
                "node": "v24.14.1",
                "ffmpeg": "ffmpeg version 9.0.2-full_build Copyright (c) 2000-2026",
                "ffprobe": "ffprobe version 9.0.2-full_build Copyright (c) 2007-2026",
            }
        ),
        free_bytes=100 * (1024**3),
    )
    assert report.ok is True
    assert report.failed_required == []
    data = report.to_dict()
    assert data["ok"] is True
    assert len(data["checks"]) == len(report.checks)


def test_audit_missing_ffmpeg_fails(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    report = run_audit(
        root=tmp_path,
        which=fake_which({"git": "C:/git.exe", "node": "C:/node.exe", "ffmpeg": None, "ffprobe": None}),
        runner=fake_runner(
            {"git": "git version 2.50.1", "node": "v24.14.1", "ffmpeg": "", "ffprobe": ""}
        ),
        free_bytes=100 * (1024**3),
    )
    assert report.ok is False
    failed = {c.name for c in report.failed_required}
    assert "tool:ffmpeg" in failed
    assert "tool:ffprobe" in failed


def test_audit_old_ffmpeg_fails(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    report = run_audit(
        root=tmp_path,
        which=fake_which({"git": "git", "node": "node", "ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}),
        runner=fake_runner(
            {
                "git": "git version 2.50.1",
                "node": "v24.14.1",
                "ffmpeg": "ffmpeg version 3.4.2 Copyright",
                "ffprobe": "ffprobe version 3.4.2 Copyright",
            }
        ),
        free_bytes=100 * (1024**3),
    )
    assert report.ok is False
    details = {c.name: c.detail for c in report.checks}
    assert "older than required" in details["tool:ffmpeg"]


def test_audit_missing_workspace_files(tmp_path: Path) -> None:
    report = run_audit(
        root=tmp_path,
        which=fake_which({"git": "git", "node": "node", "ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}),
        runner=fake_runner(
            {"git": "git version 2.50.1", "node": "v24.14.1", "ffmpeg": "ffmpeg version 9.0", "ffprobe": "ffprobe version 9.0"},
            repo=False,
        ),
        free_bytes=100 * (1024**3),
    )
    assert report.ok is False
    failed = {c.name for c in report.failed_required}
    assert "workspace-file:HYPECUT_MASTER_PROMPT.md" in failed
    assert "workspace-file:.gitignore" in failed
    assert "workspace-git-repo" in failed


def test_audit_wrong_remote(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    report = run_audit(
        root=tmp_path,
        which=fake_which({"git": "git", "node": "node", "ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}),
        runner=fake_runner(
            {"git": "git version 2.50.1", "node": "v24.14.1", "ffmpeg": "ffmpeg version 9.0", "ffprobe": "ffprobe version 9.0"},
            remote="https://github.com/someone/else.git",
        ),
        free_bytes=100 * (1024**3),
    )
    assert report.ok is False
    failed = {c.name for c in report.failed_required}
    assert "workspace-origin-remote" in failed


def test_audit_low_disk_fails(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    report = run_audit(
        root=tmp_path,
        which=fake_which({"git": "git", "node": "node", "ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}),
        runner=fake_runner(
            {"git": "git version 2.50.1", "node": "v24.14.1", "ffmpeg": "ffmpeg version 9.0", "ffprobe": "ffprobe version 9.0"}
        ),
        free_bytes=5 * (1024**3),
    )
    assert report.ok is False
    assert "disk-free" in {c.name for c in report.failed_required}


def test_cli_json_output(tmp_path: Path, capsys, monkeypatch) -> None:
    make_workspace(tmp_path)

    def fake_run(root=None, which=None, runner=None, free_bytes=None):
        return AuditReport(
            generated_at="2026-01-01T00:00:00+00:00",
            root=str(tmp_path),
            system={"platform": "test"},
            checks=[CheckResult("tool:git", passed=True, required=True, detail="git 2.50.1")],
        )

    monkeypatch.setattr("hypecut.audit.run_audit", fake_run)
    exit_code = main(["--root", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["checks"][0]["name"] == "tool:git"
