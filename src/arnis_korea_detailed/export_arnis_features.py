from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_normalized_features(path: Path, document: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def arnis_bbox_arg(bbox: dict[str, float]) -> str:
    return f"{bbox['min_lat']},{bbox['min_lng']},{bbox['max_lat']},{bbox['max_lng']}"


def arnis_compatible_export_plan(
    bbox: dict[str, float],
    arnis_output_dir: Path,
    terrain: bool = True,
    spawn_lat: float | None = None,
    spawn_lng: float | None = None,
    interior: bool | None = None,
    roof: bool | None = None,
    scale: float | None = None,
) -> dict[str, Any]:
    command = [
        "cargo",
        "run",
        "--no-default-features",
        "--",
        f"--output-dir={arnis_output_dir}",
        f"--bbox={arnis_bbox_arg(bbox)}",
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
    return {
        "adapter_mode": "wrapper_first",
        "upstream_input": "bbox_or_osm_json",
        "dry_run_command": command,
        "direct_upstream_modification": False,
    }
