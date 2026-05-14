from __future__ import annotations

import os
import shutil
import subprocess
import struct
import time
from pathlib import Path
from typing import Any


def find_renderer(root: Path) -> Path | None:
    candidates = [
        root / "bin" / "arnis-korea-renderer.exe",
        root / "bin" / "arnis-korea-renderer",
        root / "upstream" / "arnis" / "target" / "release" / "arnis",
        root / "upstream" / "arnis" / "target" / "release" / "arnis.exe",
    ]
    return next((path for path in candidates if path.exists()), None)


def _rename_single_world(output_parent: Path, world_dir: Path) -> dict[str, Any]:
    candidates = [
        path
        for path in output_parent.iterdir()
        if path.is_dir() and (path / "level.dat").exists() and (path / "region").is_dir()
    ]
    original = candidates[0] if candidates else world_dir
    if original.resolve() == world_dir.resolve():
        return {"original_arnis_world_path": str(original), "final_world_path": str(world_dir), "renamed": False}
    if world_dir.exists():
        shutil.rmtree(world_dir)
    shutil.move(str(original), str(world_dir))
    return {"original_arnis_world_path": str(original), "final_world_path": str(world_dir), "renamed": True}


def run_patched_arnis_renderer(
    root: Path,
    synthetic_osm_path: Path,
    bbox: dict[str, float],
    output_parent: Path,
    world_dir: Path,
    terrain: bool,
    interior: bool | None,
    roof: bool | None,
    spawn_lat: float | None = None,
    spawn_lng: float | None = None,
    scale: float | None = None,
) -> dict[str, Any]:
    renderer = find_renderer(root)
    if renderer is None:
        return {"executed": False, "returncode": 127, "reason": "missing_arnis_korea_renderer"}
    if world_dir.exists():
        shutil.rmtree(world_dir)
    output_parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(renderer),
        f"--file={synthetic_osm_path}",
        f"--bbox={bbox['min_lat']},{bbox['min_lng']},{bbox['max_lat']},{bbox['max_lng']}",
        f"--output-dir={output_parent}",
        "--land-cover=false",
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
    env = os.environ.copy()
    env["ARNIS_KOREA_NAVER_ONLY"] = "1"
    result = subprocess.run(command, cwd=root, check=False, text=True, encoding="utf-8", errors="replace", capture_output=True, env=env)
    move_result = _rename_single_world(output_parent, world_dir) if result.returncode == 0 else {}
    if result.returncode == 0:
        (world_dir / "session.lock").write_bytes(struct.pack(">q", int(time.time() * 1000)))
    return {
        "executed": True,
        "writer": "patched_arnis_no_network_renderer",
        "renderer_network_disabled": True,
        "synthetic_input_used": True,
        "command": command,
        "returncode": result.returncode,
        "stdout_tail": (result.stdout or "")[-4000:],
        "stderr_tail": (result.stderr or "")[-4000:],
        **move_result,
    }
