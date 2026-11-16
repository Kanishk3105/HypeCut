from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

Runner = Callable[[list[str], float], tuple[int, str]]
Which = Callable[[str], str | None]

TARGET_CPU = "i5-8250U"
TARGET_RAM_GB = 7.5
ENCODER_SMOKE_TIMEOUT = 30.0

POWERSHELL_PROBE = (
    "$ErrorActionPreference='SilentlyContinue';"
    "$cpu=Get-CimInstance Win32_Processor|Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors;"
    "$cs=Get-CimInstance Win32_ComputerSystem;"
    "$g=Get-CimInstance Win32_VideoController|ForEach-Object{[PSCustomObject]@{"
    "name=$_.Name;driver=$_.DriverVersion;"
    "adapter_ram=$(if($_.AdapterRAM){[int64]$_.AdapterRAM}else{$null})}};"
    "[PSCustomObject]@{cpu_name=$cpu.Name;cores=$cpu.NumberOfCores;logical=$cpu.NumberOfLogicalProcessors;"
    "ram_bytes=[int64]$cs.TotalPhysicalMemory;gpus=@($g)}|ConvertTo-Json -Compress -Depth 5"
)

ENCODER_LINE_RE = re.compile(r"^\s*([VAS][\.\w]{5})\s+(\S+)\s*(.*)$")
HARDWARE_ENCODER_MARKERS = ("nvenc", "qsv", "amf", "vaapi", "videotoolbox")
REGISTRY_CLASS = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
DXGI_ERROR_NOT_FOUND = 0x887A0002


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
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def parse_ps_json(text: str) -> dict:
    cleaned = text.strip().lstrip("﻿")
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("no JSON object in probe output")
    data = json.loads(cleaned[start:])
    gpus = data.get("gpus")
    if isinstance(gpus, dict):
        data["gpus"] = [gpus]
    elif gpus is None:
        data["gpus"] = []
    return data


def parse_encoders(text: str) -> list[str]:
    names: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.strip().startswith("------"):
            in_section = True
            continue
        if not in_section:
            continue
        match = ENCODER_LINE_RE.match(line)
        if match:
            names.append(match.group(2))
    return names


def parse_nvidia_smi(text: str) -> dict | None:
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3 and parts[0] and "failed" not in line.lower():
            memory = parts[2].replace(" MiB", "").replace("MB", "").strip()
            try:
                mib = int(memory)
            except ValueError:
                mib = None
            return {"name": parts[0], "driver": parts[1], "memory_mib": mib}
    return None


def _vram_from_registry_value(value: object) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, (bytes, bytearray)) and len(value) >= 8:
        return int.from_bytes(bytes(value[:8]), "little")
    return None


def dedicated_vram_registry() -> dict[str, int]:
    if os.name != "nt":
        return {}
    try:
        import winreg
    except ImportError:
        return {}
    results: dict[str, int] = {}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REGISTRY_CLASS) as base:
            index = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(base, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(base, sub_name) as sub:
                        desc, _ = winreg.QueryValueEx(sub, "DriverDesc")
                        try:
                            raw, _ = winreg.QueryValueEx(sub, "HardwareInformation.qwMemorySize")
                        except OSError:
                            continue
                        size = _vram_from_registry_value(raw)
                        if isinstance(desc, str) and size:
                            results[desc] = size
                except OSError:
                    continue
    except OSError:
        return results
    return results


class _DXGIAdapterDesc1(ctypes.Structure):
    _fields_ = [
        ("Description", ctypes.c_wchar * 128),
        ("VendorId", ctypes.c_uint),
        ("DeviceId", ctypes.c_uint),
        ("SubSysId", ctypes.c_uint),
        ("Revision", ctypes.c_uint),
        ("DedicatedVideoMemory", ctypes.c_size_t),
        ("DedicatedSystemMemory", ctypes.c_size_t),
        ("SharedSystemMemory", ctypes.c_size_t),
        ("LuidLow", ctypes.c_uint32),
        ("LuidHigh", ctypes.c_int32),
        ("Flags", ctypes.c_uint),
    ]


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def dxgi_adapters() -> list[dict]:
    if os.name != "nt":
        return []
    try:
        iid = _GUID(0x770AAE78, 0xF26F, 0x4DBA, (ctypes.c_ubyte * 8)(0xA8, 0x29, 0x25, 0x3C, 0x83, 0xD1, 0xB3, 0x87))
        dxgi = ctypes.windll.dxgi
        factory = ctypes.c_void_p()
        hr = dxgi.CreateDXGIFactory1(ctypes.byref(iid), ctypes.byref(factory))
        if hr != 0 or not factory.value:
            return []
        functype = ctypes.WINFUNCTYPE
        vtbl = ctypes.cast(factory, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
        enum_adapters1 = functype(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p))(vtbl[12])
        release_factory = functype(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
        adapters: list[dict] = []
        index = 0
        while True:
            adapter = ctypes.c_void_p()
            hr = enum_adapters1(factory, index, ctypes.byref(adapter))
            if hr != 0 or not adapter.value:
                break
            index += 1
            try:
                desc = _DXGIAdapterDesc1()
                avtbl = ctypes.cast(adapter, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
                get_desc1 = functype(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(_DXGIAdapterDesc1))(avtbl[10])
                release_adapter = functype(ctypes.c_ulong, ctypes.c_void_p)(avtbl[2])
                if get_desc1(adapter, ctypes.byref(desc)) == 0:
                    adapters.append(
                        {
                            "name": desc.Description.strip(),
                            "dedicated_bytes": int(desc.DedicatedVideoMemory),
                            "shared_bytes": int(desc.SharedSystemMemory),
                        }
                    )
            finally:
                release_adapter(adapter)
        release_factory(factory)
        return adapters
    except Exception:
        return []


def smoke_test_command(encoder: str) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=256x256:d=0.5",
        "-frames:v",
        "5",
        "-c:v",
        encoder,
        "-f",
        "null",
        "-",
    ]


def run_encoder_smoke_tests(
    encoders: list[str], runner: Runner, which: Which | None = None
) -> list[dict]:
    which = which or shutil.which
    ffmpeg = which("ffmpeg") or "ffmpeg"
    hardware = [e for e in encoders if any(marker in e for marker in HARDWARE_ENCODER_MARKERS)]
    preferred = [e for e in hardware if "h264" in e or "hevc" in e]
    other_hw = [e for e in hardware if e not in preferred]
    software = [e for e in encoders if e in ("libx264", "libx265")]
    selected = (preferred[:4] + software[:1] + other_hw)[:6]
    results: list[dict] = []
    for name in selected:
        cmd = smoke_test_command(name)
        cmd[0] = ffmpeg
        code, output = runner(cmd, ENCODER_SMOKE_TIMEOUT)
        ok = code == 0
        results.append({"encoder": name, "ok": ok, "detail": _error_detail(output, code)})
    return results


def _error_detail(output: str, code: int) -> str:
    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    if not lines:
        return "ok" if code == 0 else f"exit {code}"
    for line in lines:
        if re.search(r"error|cannot|failed|not supported|no such|denied", line, re.IGNORECASE):
            return line[:300]
    return lines[0][:300] if code != 0 else "ok"


def detect_consistent_profile(system: dict, smoke_tests: list[dict]) -> str:
    cpu = str(system.get("cpu_name") or "")
    ram_gb = float(system.get("ram_bytes") or 0) / (1024**3)
    if TARGET_CPU in cpu and abs(ram_gb - 8) < 1.0:
        return "verified-laptop-conservative"
    if smoke_tests and all(t["ok"] for t in smoke_tests if t["encoder"].startswith("libx")):
        return "generic-cpu"
    return "generic"


def collect_hardware(
    runner: Runner | None = None,
    which: Which | None = None,
    free_bytes: int | None = None,
    total_bytes: int | None = None,
    registry_vram: dict[str, int] | None = None,
    dxgi: list[dict] | None = None,
) -> dict:
    runner = runner or default_runner
    which = which or shutil.which

    code, ps_out = runner(["powershell", "-NoProfile", "-NonInteractive", "-Command", POWERSHELL_PROBE], 30.0)
    system: dict = {}
    if code == 0:
        try:
            system = parse_ps_json(ps_out)
        except (ValueError, json.JSONDecodeError):
            system = {}

    gpus_raw = system.get("gpus") or []
    if registry_vram is None:
        registry_vram = dedicated_vram_registry()
    if dxgi is None:
        dxgi = dxgi_adapters()
    dxgi_by_name = {d["name"]: d for d in dxgi}

    gpus: list[dict] = []
    for gpu in gpus_raw:
        name = str(gpu.get("name") or "unknown")
        dedicated = registry_vram.get(name)
        if dedicated is None and name in dxgi_by_name:
            dedicated = dxgi_by_name[name]["dedicated_bytes"]
        if dedicated is None:
            raw = gpu.get("adapter_ram")
            dedicated = int(raw) if isinstance(raw, (int, float)) and raw else None
        shared = dxgi_by_name.get(name, {}).get("shared_bytes")
        gpus.append(
            {
                "name": name,
                "driver": gpu.get("driver"),
                "dedicated_gb": round(dedicated / (1024**3), 2) if dedicated else None,
                "shared_gb": round(shared / (1024**3), 2) if shared else None,
            }
        )

    ffmpeg_path = which("ffmpeg")
    ffmpeg_info: dict = {"found": bool(ffmpeg_path), "version": None, "encoders": [], "encoder_tests": []}
    if ffmpeg_path:
        c, out = runner([ffmpeg_path, "-version"], 15.0)
        if c == 0:
            first = out.splitlines()[0] if out.splitlines() else ""
            m = re.search(r"version\s+(\S+)", first)
            ffmpeg_info["version"] = m.group(1) if m else None
        c, out = runner([ffmpeg_path, "-hide_banner", "-encoders"], 15.0)
        if c == 0:
            ffmpeg_info["encoders"] = parse_encoders(out)
        if ffmpeg_info["encoders"]:
            ffmpeg_info["encoder_tests"] = run_encoder_smoke_tests(ffmpeg_info["encoders"], runner, which)

    cuda: dict = {"available": False, "detail": ""}
    found_smi = which("nvidia-smi")
    fallback_smi = r"C:\Windows\System32\nvidia-smi.exe"
    if found_smi:
        smi = found_smi
    elif os.name == "nt" and Path(fallback_smi).exists():
        smi = fallback_smi
    else:
        smi = None
    if smi:
        c, out = runner([smi, "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], 15.0)
        parsed = parse_nvidia_smi(out) if c == 0 else None
        if parsed:
            cuda = {"available": True, "detail": f"{parsed['name']} driver {parsed['driver']}"}
        else:
            cuda = {"available": False, "detail": "nvidia-smi present but returned no GPU row"}
    else:
        cuda = {"available": False, "detail": "nvidia-smi not found on this system"}

    root = Path(__file__).resolve().parents[2]
    if free_bytes is None:
        try:
            usage = shutil.disk_usage(root)
            free_bytes, total_bytes = usage.free, usage.total
        except OSError:
            free_bytes, total_bytes = free_bytes or 0, total_bytes or 0

    profile = detect_consistent_profile(system, ffmpeg_info["encoder_tests"])
    return {
        "cpu": {
            "name": system.get("cpu_name") or platform.processor() or "unknown",
            "cores_physical": system.get("cores"),
            "cores_logical": system.get("logical") or os.cpu_count(),
        },
        "ram": {"total_gb": round((system.get("ram_bytes") or 0) / (1024**3), 1)},
        "gpus": gpus,
        "ffmpeg": ffmpeg_info,
        "cuda": cuda,
        "disk": {
            "free_gb": round(free_bytes / (1024**3), 1),
            "total_gb": round((total_bytes or 0) / (1024**3), 1),
        },
        "profile": profile,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HypeCut hardware diagnostics")
    parser.add_argument("--json", action="store_true", help="print full JSON report")
    args = parser.parse_args(argv)

    report = collect_hardware()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("HypeCut hardware diagnostics")
        cpu = report["cpu"]
        print(f"  CPU: {cpu['name']} ({cpu['cores_physical']}C/{cpu['cores_logical']}T)")
        print(f"  RAM: {report['ram']['total_gb']} GB")
        for gpu in report["gpus"]:
            print(f"  GPU: {gpu['name']} driver={gpu['driver']} dedicated={gpu['dedicated_gb']} GB shared={gpu['shared_gb']} GB")
        ff = report["ffmpeg"]
        print(f"  FFmpeg: {ff['version'] or 'NOT FOUND'} ({len(ff['encoders'])} encoders)")
        for test in ff["encoder_tests"]:
            mark = "OK" if test["ok"] else "FAIL"
            print(f"    [{mark}] {test['encoder']}: {test['detail']}")
        print(f"  CUDA: {'yes' if report['cuda']['available'] else 'no'} — {report['cuda']['detail']}")
        print(f"  Disk free: {report['disk']['free_gb']} GB")
        print(f"  Profile: {report['profile']}")
    return 0 if report["ffmpeg"]["found"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
