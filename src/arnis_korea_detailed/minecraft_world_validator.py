from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any


ALLOWED_WORLD_ROOT_NAMES = {
    "level.dat",
    "session.lock",
    "region",
    "data",
    "datapacks",
    "icon.png",
    "level.dat_old",
    "playerdata",
}

FORBIDDEN_WORLD_ROOT_NAMES = {
    "naver_raster",
    "features.normalized.json",
    "naver_synthetic_osm.json",
    "naver_world_features.json",
    "source-policy-report.json",
    "arnis-korea-quality-report.md",
    "world_validation.json",
    "debug",
    "logs",
}


def _basic_level_dat_parse(path: Path) -> dict[str, Any]:
    try:
        raw = gzip.decompress(path.read_bytes())
    except Exception as exc:
        return {"parseable": False, "error": f"gzip:{type(exc).__name__}"}
    if not raw or raw[0] != 10:
        return {"parseable": False, "error": "root_tag_is_not_compound"}
    required_strings = [b"Data", b"LevelName", b"DataVersion", b"Version", b"WorldGenSettings", b"SpawnX", b"SpawnY", b"SpawnZ"]
    missing = [item.decode("ascii") for item in required_strings if item not in raw]
    return {"parseable": not missing, "missing_markers": missing, "bytes": len(raw)}


def validate_world_layout(world_dir: Path, metadata_dir: Path, write_report: bool = True) -> dict[str, Any]:
    region_dir = world_dir / "region"
    mca_files = sorted(region_dir.glob("*.mca")) if region_dir.is_dir() else []
    root_entries = {path.name for path in world_dir.iterdir()} if world_dir.exists() else set()
    forbidden_entries = sorted(root_entries & FORBIDDEN_WORLD_ROOT_NAMES)
    unexpected_entries = sorted(root_entries - ALLOWED_WORLD_ROOT_NAMES)
    mca_sizes = {path.name: path.stat().st_size for path in mca_files}
    report = {
        "schema": "arnis-korea.minecraft_world_validation.v1",
        "world_dir": str(world_dir),
        "metadata_dir": str(metadata_dir),
        "target_minecraft_java_version": "1.21.x",
        "checks": {
            "world_dir_exists": world_dir.is_dir(),
            "level_dat_exists": (world_dir / "level.dat").is_file(),
            "session_lock_exists": (world_dir / "session.lock").is_file(),
            "region_dir_exists": region_dir.is_dir(),
            "mca_count": len(mca_files),
            "mca_size_min_bytes": min(mca_sizes.values()) if mca_sizes else 0,
            "forbidden_world_root_entries": forbidden_entries,
            "unexpected_world_root_entries": unexpected_entries,
            "source_policy_report_in_metadata": (metadata_dir / "source-policy-report.json").is_file(),
            "quality_report_in_metadata": (metadata_dir / "arnis-korea-quality-report.md").is_file(),
            "level_dat_parse": _basic_level_dat_parse(world_dir / "level.dat") if (world_dir / "level.dat").is_file() else {"parseable": False, "error": "missing"},
        },
    }
    checks = report["checks"]
    report["valid"] = bool(
        checks["world_dir_exists"]
        and checks["level_dat_exists"]
        and checks["session_lock_exists"]
        and checks["region_dir_exists"]
        and checks["mca_count"] >= 1
        and checks["mca_size_min_bytes"] > 8192
        and not checks["forbidden_world_root_entries"]
        and not checks["unexpected_world_root_entries"]
        and checks["source_policy_report_in_metadata"]
        and checks["quality_report_in_metadata"]
        and checks["level_dat_parse"].get("parseable")
    )
    if write_report:
        metadata_dir.mkdir(parents=True, exist_ok=True)
        (metadata_dir / "world_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
