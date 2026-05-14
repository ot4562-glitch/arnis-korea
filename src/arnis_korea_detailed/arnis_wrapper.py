from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .export_arnis_features import arnis_compatible_export_plan

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]


def build_arnis_command(
    bbox: dict[str, float],
    arnis_output_dir: Path,
    terrain: bool = True,
    spawn_lat: float | None = None,
    spawn_lng: float | None = None,
    interior: bool | None = None,
    roof: bool | None = None,
    scale: float | None = None,
) -> list[str]:
    return arnis_compatible_export_plan(
        bbox,
        arnis_output_dir,
        terrain=terrain,
        spawn_lat=spawn_lat,
        spawn_lng=spawn_lng,
        interior=interior,
        roof=roof,
        scale=scale,
    )["dry_run_command"]


def packaged_arnis_command(
    bbox: dict[str, float],
    arnis_output_dir: Path,
    terrain: bool,
    spawn_lat: float | None = None,
    spawn_lng: float | None = None,
    interior: bool | None = None,
    roof: bool | None = None,
    scale: float | None = None,
) -> list[str] | None:
    candidates = [ROOT / "bin" / "arnis-upstream.exe", ROOT / "bin" / "arnis-upstream", ROOT / "arnis-upstream.exe", ROOT / "arnis-upstream"]
    binary = next((candidate for candidate in candidates if candidate.exists()), None)
    if binary is None:
        return None
    command = [
        str(binary),
        f"--output-dir={arnis_output_dir}",
        f"--bbox={bbox['min_lat']},{bbox['min_lng']},{bbox['max_lat']},{bbox['max_lng']}",
    ]
    if terrain:
        command.append("--terrain")
    if interior is not None:
        command.append(f"--interior={str(interior).lower()}")
    if roof is not None:
        command.append(f"--roof={str(roof).lower()}")
    if spawn_lat is not None:
        command.append(f"--spawn-lat={spawn_lat}")
    if spawn_lng is not None:
        command.append(f"--spawn-lng={spawn_lng}")
    if scale is not None:
        command.append(f"--scale={scale}")
    return command


def run_arnis_if_explicit(
    bbox: dict[str, float],
    arnis_output_dir: Path,
    upstream_dir: Path,
    execute: bool = False,
    terrain: bool = True,
    spawn_lat: float | None = None,
    spawn_lng: float | None = None,
    interior: bool | None = None,
    roof: bool | None = None,
    scale: float | None = None,
) -> dict[str, object]:
    packaged_command = packaged_arnis_command(
        bbox,
        arnis_output_dir,
        terrain,
        spawn_lat=spawn_lat,
        spawn_lng=spawn_lng,
        interior=interior,
        roof=roof,
        scale=scale,
    )
    command = packaged_command or arnis_compatible_export_plan(
        bbox,
        arnis_output_dir,
        terrain=terrain,
        spawn_lat=spawn_lat,
        spawn_lng=spawn_lng,
        interior=interior,
        roof=roof,
        scale=scale,
    )["dry_run_command"]
    if not execute:
        return {"executed": False, "command": command}
    if packaged_command is None and not upstream_dir.exists():
        return {"executed": False, "reason": "missing_upstream_arnis", "command": command}
    result = subprocess.run(
        command,
        cwd=upstream_dir if packaged_command is None else ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    return {
        "executed": True,
        "command": command,
        "returncode": result.returncode,
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
    }
