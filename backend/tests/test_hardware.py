from __future__ import annotations

import json
from pathlib import Path

import pytest

from hypecut.hardware import (
    POWERSHELL_PROBE,
    collect_hardware,
    dedicated_vram_registry,
    detect_consistent_profile,
    dxgi_adapters,
    main,
    parse_encoders,
    parse_nvidia_smi,
    parse_ps_json,
    run_encoder_smoke_tests,
    smoke_test_command,
    _vram_from_registry_value,
)

ENCODERS_OUTPUT = """Encoders:
 V..... = Video
 A..... = Audio
 S..... = Subtitle
 .F.... = Frame-level multithreading
 ..S... = Slice-level multithreading
 ...X.. = Codec is experimental
 ....B = Supports draw_horiz_band
 ------
 V....D libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)
 V....D h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)
 V..... h264_qsv             H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (Intel Quick Sync Video acceleration) (codec h264)
 V....D hevc_nvenc           NVIDIA NVENC hevc encoder (codec hevc)
 A....D aac                  AAC (Advanced Audio Coding)
"""

PS_JSON = json.dumps(
    {
        "cpu_name": "Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz",
        "cores": 4,
        "logical": 8,
        "ram_bytes": 8493430272,
        "gpus": [
            {"name": "Intel(R) UHD Graphics 620", "driver": "26.20.100.7372", "adapter_ram": 1073741824},
            {"name": "NVIDIA GeForce MX130", "driver": "30.0.15.1169", "adapter_ram": 2147483648},
        ],
    }
)

REGISTRY_VRAM = {"NVIDIA GeForce MX130": 2147483648}
DXGI_ADAPTERS = [
    {"name": "Intel(R) UHD Graphics 620", "dedicated_bytes": 134217728, "shared_bytes": 4294967296},
    {"name": "NVIDIA GeForce MX130", "dedicated_bytes": 2147483648, "shared_bytes": 4294967296},
]

VERSION_OUTPUT = "ffmpeg version 9.0.2-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers\n"


def make_runner(
    *,
    ps_json: str = PS_JSON,
    encoders: str = ENCODERS_OUTPUT,
    version: str = VERSION_OUTPUT,
    smoke: dict[str, tuple[int, str]] | None = None,
    smi_csv: str | None = "NVIDIA GeForce MX130, 30.0.15.1169, 2048 MiB",
):
    smoke = smoke or {}

    def run(args: list[str], timeout: float) -> tuple[int, str]:
        exe = Path(args[0]).stem.lower()
        if exe == "powershell":
            return 0, ps_json
        if exe == "ffmpeg":
            if "-version" in args:
                return 0, version
            if "-encoders" in args:
                return 0, encoders
            idx = args.index("-c:v")
            encoder = args[idx + 1]
            return smoke.get(encoder, (0, ""))
        if exe == "nvidia-smi":
            if smi_csv is None:
                return 1, ""
            return 0, smi_csv + "\n"
        return 1, ""

    return run


def fake_which(mapping: dict[str, str | None]):
    return lambda name: mapping.get(name)


WHICH = fake_which(
    {
        "ffmpeg": "C:/ffmpeg/bin/ffmpeg.exe",
        "ffprobe": "C:/ffmpeg/bin/ffprobe.exe",
        "nvidia-smi": "C:/nvidia-smi.exe",
        "powershell": "powershell",
    }
)


def test_parse_ps_json_list_and_single_object() -> None:
    data = parse_ps_json(PS_JSON)
    assert data["cpu_name"].startswith("Intel")
    assert len(data["gpus"]) == 2

    single = parse_ps_json('{"cpu_name":"x","gpus":{"name":"GPU-Only"}}')
    assert isinstance(single["gpus"], list) and len(single["gpus"]) == 1

    none = parse_ps_json('{"cpu_name":"x"}')
    assert none["gpus"] == []


def test_parse_ps_json_invalid() -> None:
    with pytest.raises(ValueError):
        parse_ps_json("no json here")


def test_parse_encoders_real_format() -> None:
    names = parse_encoders(ENCODERS_OUTPUT)
    assert names == ["libx264", "h264_nvenc", "h264_qsv", "hevc_nvenc", "aac"]
    legend_not_included = "Video" not in names


def test_parse_nvidia_smi() -> None:
    parsed = parse_nvidia_smi("NVIDIA GeForce MX130, 30.0.15.1169, 2048 MiB\n")
    assert parsed == {"name": "NVIDIA GeForce MX130", "driver": "30.0.15.1169", "memory_mib": 2048}
    assert parse_nvidia_smi("Failed to initialize NVML") is None
    assert parse_nvidia_smi("") is None


def test_vram_from_registry_value() -> None:
    assert _vram_from_registry_value(2147483648) == 2147483648
    assert _vram_from_registry_value((2).to_bytes(8, "little")) == 2
    assert _vram_from_registry_value(None) is None
    assert _vram_from_registry_value("nope") is None


def test_smoke_test_command_is_arg_array() -> None:
    cmd = smoke_test_command("h264_nvenc")
    assert cmd[0] == "ffmpeg"
    assert "h264_nvenc" in cmd
    assert "-c:v" in cmd
    assert all(isinstance(part, str) for part in cmd)


def test_run_encoder_smoke_tests_selects_hardware_and_software() -> None:
    runner = make_runner(
        smoke={
            "h264_nvenc": (0, ""),
            "hevc_nvenc": (1, "Error: nvenc not supported\n"),
            "h264_qsv": (0, ""),
            "libx264": (0, ""),
        }
    )
    results = run_encoder_smoke_tests(
        ["libx264", "h264_nvenc", "hevc_nvenc", "h264_qsv", "aac"],
        runner,
        WHICH,
    )
    by_name = {r["encoder"]: r for r in results}
    assert by_name["h264_nvenc"]["ok"] is True
    assert by_name["hevc_nvenc"]["ok"] is False
    assert "nvenc not supported" in by_name["hevc_nvenc"]["detail"]
    assert "libx264" in by_name
    assert "aac" not in by_name
    assert len(results) <= 6


def test_detect_consistent_profile_verified_laptop() -> None:
    system = {"cpu_name": "Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz", "ram_bytes": 8493430272}
    assert detect_consistent_profile(system, []) == "verified-laptop-conservative"


def test_detect_consistent_profile_generic() -> None:
    system = {"cpu_name": "AMD Ryzen 7", "ram_bytes": 32 * (1024**3)}
    assert detect_consistent_profile(system, [{"encoder": "libx264", "ok": True, "detail": "ok"}]) == "generic-cpu"


def test_collect_hardware_full_report() -> None:
    report = collect_hardware(
        runner=make_runner(smoke={"hevc_nvenc": (1, "fail")}),
        which=WHICH,
        free_bytes=150 * (1024**3),
        total_bytes=512 * (1024**3),
        registry_vram=REGISTRY_VRAM,
        dxgi=DXGI_ADAPTERS,
    )
    assert report["cpu"]["name"].startswith("Intel(R) Core(TM) i5-8250U")
    assert report["cpu"]["cores_physical"] == 4
    assert report["cpu"]["cores_logical"] == 8
    assert report["ram"]["total_gb"] == 7.9

    gpus = {g["name"]: g for g in report["gpus"]}
    mx130 = gpus["NVIDIA GeForce MX130"]
    assert mx130["dedicated_gb"] == 2.0
    assert mx130["shared_gb"] == 4.0
    assert mx130["driver"] == "30.0.15.1169"
    intel = gpus["Intel(R) UHD Graphics 620"]
    assert intel["dedicated_gb"] == 0.12
    assert intel["shared_gb"] == 4.0

    ff = report["ffmpeg"]
    assert ff["found"] is True
    assert ff["version"].startswith("9.0.2")
    assert "h264_nvenc" in ff["encoders"]
    tests = {t["encoder"]: t for t in ff["encoder_tests"]}
    assert tests["hevc_nvenc"]["ok"] is False
    assert tests["h264_nvenc"]["ok"] is True

    assert report["cuda"]["available"] is True
    assert "MX130" in report["cuda"]["detail"]
    assert report["disk"]["free_gb"] == 150.0
    assert report["profile"] == "verified-laptop-conservative"


def test_collect_hardware_without_ffmpeg() -> None:
    report = collect_hardware(
        runner=make_runner(),
        which=fake_which({"ffmpeg": None, "ffprobe": None, "nvidia-smi": None}),
        free_bytes=10 * (1024**3),
        total_bytes=100 * (1024**3),
        registry_vram={},
        dxgi=[],
    )
    assert report["ffmpeg"]["found"] is False
    assert report["ffmpeg"]["encoders"] == []
    assert report["cuda"]["available"] is False


def test_dxgi_adapters_returns_list() -> None:
    result = dxgi_adapters()
    assert isinstance(result, list)
    if result:
        assert "name" in result[0]
        assert "shared_bytes" in result[0]


def test_cli_json(capsys, monkeypatch) -> None:
    fixed = {
        "cpu": {"name": "x", "cores_physical": 1, "cores_logical": 2},
        "ram": {"total_gb": 8},
        "gpus": [],
        "ffmpeg": {"found": True, "version": "9.0", "encoders": [], "encoder_tests": []},
        "cuda": {"available": False, "detail": ""},
        "disk": {"free_gb": 1.0, "total_gb": 2.0},
        "profile": "generic",
    }
    monkeypatch.setattr("hypecut.hardware.collect_hardware", lambda: fixed)
    code = main(["--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert json.loads(out)["ffmpeg"]["found"] is True


def test_powershell_probe_is_constant() -> None:
    assert "Get-CimInstance Win32_Processor" in POWERSHELL_PROBE
    assert "ConvertTo-Json" in POWERSHELL_PROBE


def test_registry_probe_does_not_raise() -> None:
    result = dedicated_vram_registry()
    assert isinstance(result, dict)
