#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from arnis_korea_detailed.arnis_wrapper import run_arnis_if_explicit
from arnis_korea_detailed.arnis_no_network_renderer import run_patched_arnis_renderer
from arnis_korea_detailed.export_arnis_features import arnis_compatible_export_plan, write_normalized_features
from arnis_korea_detailed.geometry_cleanup import cleanup_features
from arnis_korea_detailed.korea_feature_schema import (
    HEIGHT_SOURCE_PRIORITY,
    MINECRAFT_PALETTE_NOTES,
    STYLE_PROFILES,
    normalized_document,
)
from arnis_korea_detailed.minimal_world_writer import write_world
from arnis_korea_detailed.minecraft_world_validator import ALLOWED_WORLD_ROOT_NAMES, FORBIDDEN_WORLD_ROOT_NAMES, validate_world_layout
from arnis_korea_detailed.mock_raster_provider import create_mock_raster
from arnis_korea_detailed.naver_synthetic_layer import write_synthetic_layer
from arnis_korea_detailed.naver_static_map_provider import (
    download_static_map_if_allowed,
    key_source_status,
    probe_static_map,
)
from arnis_korea_detailed.raster_mosaic import single_image_mosaic
from arnis_korea_detailed.segment_map_image import segment_pixels
from arnis_korea_detailed.output_layout import DEFAULT_WORLD_NAME, PROJECT_DIR_NAME, build_output_layout
from arnis_korea_detailed.source_policy import write_source_policy_report
from arnis_korea_detailed.static_map_request_planner import split_static_map_requests
from arnis_korea_detailed.vectorize_features import vectorize_segments

VERSION = "0.5.2"
STATIC_TERMS_FLAG = "--accept-naver-static-raster-terms"
FORBIDDEN_OUTPUT_MARKERS = (
    "/mnt/minecraft-data/server/world",
    "\\mnt\\minecraft-data\\server\\world",
    "minecraft-data/server/world",
    "minecraft-data\\server\\world",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_bbox_path(path: Path) -> dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return normalize_bbox(data.get("bbox", data))


def parse_bbox(value: str | None, bbox_file: Path | None) -> dict[str, float]:
    if value:
        parts = [float(part.strip()) for part in value.split(",")]
        if len(parts) != 4:
            raise ValueError("--bbox must be min_lat,min_lng,max_lat,max_lng")
        return normalize_bbox({"min_lat": parts[0], "min_lng": parts[1], "max_lat": parts[2], "max_lng": parts[3]})
    if bbox_file:
        return load_bbox_path(bbox_file)
    raise ValueError("provide --bbox or --bbox-file")


def normalize_bbox(bbox: dict[str, Any]) -> dict[str, float]:
    required = {"min_lat", "min_lng", "max_lat", "max_lng"}
    missing = required - set(bbox)
    if missing:
        raise ValueError(f"bbox missing keys: {sorted(missing)}")
    normalized = {key: float(bbox[key]) for key in required}
    if normalized["min_lat"] >= normalized["max_lat"] or normalized["min_lng"] >= normalized["max_lng"]:
        raise ValueError("bbox min values must be lower than max values")
    return normalized


def load_simple_config(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    config: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        config[key.strip()] = value.strip().strip('"').strip("'")
    return config


def safe_output_dir(path: Path) -> Path:
    resolved = path.resolve()
    raw = str(path).replace("\\", "/").lower()
    resolved_text = str(resolved).replace("\\", "/").lower()
    for marker in FORBIDDEN_OUTPUT_MARKERS:
        marker_text = marker.replace("\\", "/").lower()
        if marker_text in raw or marker_text in resolved_text:
            raise ValueError(f"refusing live Minecraft server world output: {resolved}")
    return resolved


def naver_key_paths(args: argparse.Namespace) -> tuple[Path | None, Path | None]:
    config = load_simple_config(getattr(args, "config", None))
    key_id = getattr(args, "naver_key_id_file", None) or config.get("naver_key_id_file")
    key = getattr(args, "naver_key_file", None) or config.get("naver_key_file")
    return (Path(key_id) if key_id else None, Path(key) if key else None)


def plan_static(args: argparse.Namespace) -> dict[str, Any]:
    bbox = parse_bbox(getattr(args, "bbox", None), getattr(args, "bbox_file", None))
    plan = split_static_map_requests(
        bbox=bbox,
        level=args.level,
        width=args.width,
        height=args.height,
        scale=args.scale,
        maptype=args.maptype,
        fmt=args.format,
        dataversion=args.dataversion,
    )
    if getattr(args, "output", None):
        write_normalized_features(args.output, plan)
    return plan


def raster_features_from_path(raster: Path, bbox: dict[str, float]) -> list[Any]:
    pixels = single_image_mosaic(raster)
    return cleanup_features(vectorize_segments(segment_pixels(pixels), bbox))


def mock_features(args: argparse.Namespace, bbox: dict[str, float] | None = None) -> tuple[list[Any], Path]:
    bbox = bbox or parse_bbox(getattr(args, "bbox", None), getattr(args, "bbox_file", None))
    raster = create_mock_raster(args.mock_raster, args.mock_width, args.mock_height)
    features = raster_features_from_path(raster, bbox)
    return features, raster


def verify_world_files(output_dir: Path) -> dict[str, Any]:
    return {
        "level_dat": (output_dir / "level.dat").exists(),
        "region_dir": (output_dir / "region").is_dir(),
        "mca_files": len(list((output_dir / "region").glob("*.mca"))) if (output_dir / "region").is_dir() else 0,
    }


def write_feature_document(args: argparse.Namespace, source: str, features: list[Any], bbox: dict[str, float], metadata: dict[str, Any], output_dir: Path | None = None) -> Path:
    document = normalized_document(
        bbox=bbox,
        source_mode=source,
        features=features,
        metadata={
            **metadata,
            "created_at": _now(),
            "source": source,
            "license_gate": {
                "naver_static_raster_storage": getattr(args, "allow_static_raster_storage", False),
                "naver_static_raster_analysis": getattr(args, "allow_static_raster_analysis", False),
                "naver_static_raster_terms_accepted": getattr(args, "accept_naver_static_raster_terms", False),
                "official_api_only": True,
            },
            "korea_productization": {
                "style_profiles": STYLE_PROFILES,
                "height_source_priority": HEIGHT_SOURCE_PRIORITY,
                "minecraft_palette_notes": MINECRAFT_PALETTE_NOTES,
            },
        },
    )
    return write_normalized_features((output_dir or args.output_dir) / "features.normalized.json", document)


def minecraft_saves_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / ".minecraft" / "saves"
    return Path.home() / ".minecraft" / "saves"


def copy_playable_world_to_saves(world_dir: Path, saves_dir: Path | None = None, overwrite: bool = False) -> dict[str, Any]:
    saves = saves_dir or minecraft_saves_dir()
    saves.mkdir(parents=True, exist_ok=True)
    destination = saves / world_dir.name
    if destination.exists() and not overwrite:
        base = destination
        index = 2
        while destination.exists():
            destination = base.with_name(f"{base.name}-{index}")
            index += 1
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(world_dir, destination, ignore=shutil.ignore_patterns(PROJECT_DIR_NAME, "naver_raster", "*.json", "*.md", "debug", "logs"))
    return {"executed": True, "source": str(world_dir), "destination": str(destination)}


def clean_world_root(world_dir: Path) -> list[str]:
    removed: list[str] = []
    if not world_dir.exists():
        return removed
    for child in world_dir.iterdir():
        if child.name not in ALLOWED_WORLD_ROOT_NAMES:
            removed.append(child.name)
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    return removed


def cmd_plan_static(args: argparse.Namespace) -> int:
    print(json.dumps(plan_static(args), ensure_ascii=False, indent=2))
    return 0


def cmd_probe_naver(args: argparse.Namespace) -> int:
    plan = plan_static(args)
    key_id_file, key_file = naver_key_paths(args)
    result = probe_static_map(plan["tiles"][0]["params"], key_id_file=key_id_file, key_file=key_file)
    print(json.dumps({"endpoint": plan["endpoint"], "key_status": key_source_status(key_id_file, key_file), "probe": result}, ensure_ascii=False, indent=2))
    return 0


def cmd_download_static(args: argparse.Namespace) -> int:
    args.output_dir = safe_output_dir(args.output_dir)
    layout = build_output_layout(args.output_dir, getattr(args, "world_name", None), getattr(args, "project_metadata_dir", None))
    layout.metadata_dir.mkdir(parents=True, exist_ok=True)
    if not (args.allow_static_raster_storage and args.allow_static_raster_analysis and args.accept_naver_static_raster_terms):
        raise ValueError(f"download-static requires --allow-static-raster-storage --allow-static-raster-analysis {STATIC_TERMS_FLAG}")
    plan = plan_static(args)
    key_id_file, key_file = naver_key_paths(args)
    result = download_static_map_if_allowed(
        plan["tiles"][0]["params"],
        layout.metadata_dir / "naver_raster" / args.output_name,
        allow_storage=args.allow_static_raster_storage,
        allow_analysis=args.allow_static_raster_analysis,
        key_id_file=key_id_file,
        key_file=key_file,
    )
    print(json.dumps({"endpoint": plan["endpoint"], "download": result}, ensure_ascii=False, indent=2))
    return 0 if result.get("executed") else 2


def cmd_mock_vectorize(args: argparse.Namespace) -> int:
    args.output_dir = safe_output_dir(args.output_dir)
    layout = build_output_layout(args.output_dir, getattr(args, "world_name", None), getattr(args, "project_metadata_dir", None))
    layout.metadata_dir.mkdir(parents=True, exist_ok=True)
    bbox = parse_bbox(args.bbox, args.bbox_file)
    features, raster = mock_features(args, bbox)
    path = write_feature_document(args, "mock_raster", features, bbox, {"mock_raster": str(raster)}, layout.metadata_dir)
    print(json.dumps({"features": str(path), "feature_count": len(features), "mock_raster": str(raster)}, ensure_ascii=False, indent=2))
    return 0


def cmd_export_features(args: argparse.Namespace) -> int:
    args.output_dir = safe_output_dir(args.output_dir)
    layout = build_output_layout(args.output_dir, getattr(args, "world_name", None), getattr(args, "project_metadata_dir", None))
    layout.metadata_dir.mkdir(parents=True, exist_ok=True)
    bbox = parse_bbox(args.bbox, args.bbox_file)
    if args.source == "mock":
        features, raster = mock_features(args, bbox)
        metadata = {"mock_raster": str(raster)}
    else:
        features = []
        metadata = {"export_mode": "empty_osm_base_features"}
    path = write_feature_document(args, args.source, features, bbox, metadata, layout.metadata_dir)
    print(json.dumps({"features": str(path), "feature_count": len(features)}, ensure_ascii=False, indent=2))
    return 0


def cmd_selector(args: argparse.Namespace) -> int:
    selector = ROOT / "web" / "dynamic_selector.html"
    if args.output_bbox:
        bbox = {
            "center": {"lon": 127.059, "lat": 37.597},
            "level": 16,
            "bbox": {"min_lat": 37.5955, "min_lng": 127.0555, "max_lat": 37.5985, "max_lng": 127.0620},
        }
        args.output_bbox.parent.mkdir(parents=True, exist_ok=True)
        args.output_bbox.write_text(json.dumps(bbox, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selector_file": str(selector), "output_bbox": str(args.output_bbox) if args.output_bbox else None}, ensure_ascii=False, indent=2))
    return 0


def cmd_repair_world_layout(args: argparse.Namespace) -> int:
    source = safe_output_dir(args.input)
    output = safe_output_dir(args.output)
    metadata_dir = args.project_metadata_dir or (output.parent / PROJECT_DIR_NAME)
    if output.exists() and args.overwrite:
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in ALLOWED_WORLD_ROOT_NAMES:
        src = source / name
        if not src.exists():
            continue
        dst = output / name
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        copied.append(name)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    for name in FORBIDDEN_WORLD_ROOT_NAMES:
        src = source / name
        if not src.exists():
            continue
        dst = metadata_dir / name
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    validation = validate_world_layout(output, metadata_dir)
    result = {
        "input": str(source),
        "output": str(output),
        "project_metadata_dir": str(metadata_dir),
        "copied_world_entries": sorted(copied),
        "warning": "layout_repaired_but_writer_may_be_invalid",
        "validation": validation,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if validation.get("valid") else 2


def cmd_generate(args: argparse.Namespace) -> int:
    args.output_dir = safe_output_dir(args.output_dir)
    layout = build_output_layout(args.output_dir, args.world_name, args.project_metadata_dir)
    layout.output_dir.mkdir(parents=True, exist_ok=True)
    layout.metadata_dir.mkdir(parents=True, exist_ok=True)
    layout.world_dir.mkdir(parents=True, exist_ok=True)
    bbox = parse_bbox(args.bbox, args.bbox_file)
    if args.source == "naver-assisted":
        raise ValueError("naver-assisted hybrid mode is reserved and not implemented in v0.5; use naver-only or mock-naver")
    static_result = {"executed": False, "reason": "source_not_naver_static"}
    features: list[Any] = []
    metadata: dict[str, Any] = {
        "terrain": args.terrain,
        "spawn": {"lat": args.spawn_lat, "lng": args.spawn_lng},
        "interior": args.interior,
        "roof": args.roof,
        "building_mode": {
            "value": args.building_mode,
            "status": "MVP mode",
            "note": "현재 building-mode는 upstream Arnis 직접 옵션이 아니라 Arnis Korea metadata로 기록됩니다.",
        },
        "source_policy": "naver_only" if args.source in {"naver-only", "mock-naver", "naver-static"} else "legacy_or_hybrid",
    }

    if args.source in {"mock", "mock-naver"}:
        features, raster = mock_features(args, bbox)
        metadata["mock_raster"] = str(raster)
    elif args.source in {"naver-static", "naver-only"}:
        if not (args.allow_static_raster_storage and args.allow_static_raster_analysis and args.accept_naver_static_raster_terms):
            raise ValueError(f"{args.source} requires --allow-static-raster-storage --allow-static-raster-analysis {STATIC_TERMS_FLAG}")
        plan = plan_static(args)
        if len(plan.get("tiles", [])) > args.max_static_requests:
            raise ValueError(f"Static Map request plan has {len(plan.get('tiles', []))} requests; max is {args.max_static_requests}")
        key_id_file, key_file = naver_key_paths(args)
        raster_dir = layout.metadata_dir / "naver_raster"
        raster_name = f"static_{args.maptype}_000.{args.format.replace('jpeg', 'jpg').replace('png8', 'png')}"
        static_result = download_static_map_if_allowed(
            plan["tiles"][0]["params"],
            raster_dir / raster_name,
            allow_storage=args.allow_static_raster_storage,
            allow_analysis=args.allow_static_raster_analysis,
            key_id_file=key_id_file,
            key_file=key_file,
        )
        if not static_result.get("executed"):
            raise ValueError(f"official Naver Static Map download did not execute: {static_result.get('reason')}")
        features = raster_features_from_path(Path(static_result["output_path"]), bbox)
        metadata["static_map_request_plan"] = plan
        metadata["static_map_download"] = static_result

    feature_path = write_feature_document(args, args.source, features, bbox, metadata, layout.metadata_dir)
    arnis_result = {"executed": False, "reason": "source_not_osm"}
    if args.source == "osm":
        arnis_result = run_arnis_if_explicit(
            bbox,
            layout.world_dir,
            args.arnis_upstream,
            execute=True,
            terrain=args.terrain,
            spawn_lat=args.spawn_lat,
            spawn_lng=args.spawn_lng,
            interior=args.interior,
            roof=args.roof,
            scale=args.arnis_scale,
        )
    world_result: dict[str, Any] = {"executed": False, "reason": "source_not_naver_only"}
    synthetic_paths: dict[str, str] = {}
    if args.source in {"naver-only", "mock-naver", "naver-static"}:
        synthetic_paths = write_synthetic_layer(layout.metadata_dir, features, bbox, args.source, args.building_mode)
        terrain_source = "naver_terrain_raster_estimated" if args.terrain and args.maptype == "terrain" else "flat"
        if args.writer == "minimal-debug":
            world_result = write_world(
                layout.world_dir,
                layout.metadata_dir,
                Path(synthetic_paths["world_features"]),
                bbox,
                args.source,
                terrain_source,
                args.building_mode,
                world_name=layout.world_name,
            )
            world_result["compatibility_warning"] = True
        else:
            world_result = run_patched_arnis_renderer(
                ROOT,
                Path(synthetic_paths["synthetic_osm"]),
                bbox,
                layout.output_dir,
                layout.world_dir,
                terrain=args.terrain,
                interior=args.interior,
                roof=args.roof,
                spawn_lat=args.spawn_lat,
                spawn_lng=args.spawn_lng,
                scale=args.arnis_scale,
            )
            if world_result.get("returncode") != 0:
                raise ValueError(f"patched Arnis renderer failed: {world_result.get('reason') or world_result.get('stderr_tail')}")
            quality_report = layout.metadata_dir / "arnis-korea-quality-report.md"
            quality_report.write_text(
                "\n".join(
                    [
                        "# Arnis Korea v0.5.2 Naver-only Quality Report",
                        "",
                        f"- writer: {world_result['writer']}",
                        "- renderer_network_disabled: true",
                        "- synthetic_input_used: true",
                        f"- source_mode: {args.source}",
                        f"- world_name: {layout.world_name}",
                        f"- terrain_source: {terrain_source}",
                        "- external_non_naver_sources_used: false",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
        if args.clean_world_root and not args.keep_debug_in_world_root:
            world_result["cleaned_world_root_entries"] = clean_world_root(layout.world_dir)
        source_report = write_source_policy_report(
            layout.metadata_dir / "source-policy-report.json",
            args.source,
            {
                "static_map": static_result,
                "synthetic_layer": synthetic_paths,
                "world": world_result,
                "renderer_network_disabled": True,
                "synthetic_input_used": True,
            },
        )
        world_result["source_policy_report"] = str(source_report)
        validation = validate_world_layout(layout.world_dir, layout.metadata_dir)
        world_result["validation"] = validation
        export_result = copy_playable_world_to_saves(layout.world_dir) if args.minecraft_saves_export else {"executed": False}
        world_result["minecraft_saves_export"] = export_result
    else:
        validation = {"valid": None, "reason": "source_not_naver_only"}
    result = {
        "output_dir": str(layout.output_dir),
        "playable_world_dir": str(layout.world_dir),
        "project_metadata_dir": str(layout.metadata_dir),
        "world_name": layout.world_name,
        "features": str(feature_path),
        "synthetic_layer": synthetic_paths,
        "arnis": arnis_result,
        "world": world_result,
        "world_verification": verify_world_files(layout.world_dir),
        "world_validation": validation,
        "static_map": static_result,
        "source_policy": {
            "source_policy": "naver_only" if args.source in {"naver-only", "mock-naver", "naver-static"} else "legacy_or_hybrid",
            "external_non_naver_sources_used": False if args.source in {"naver-only", "mock-naver", "naver-static"} else None,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if arnis_result.get("returncode", 0) == 0 else int(arnis_result.get("returncode", 1))


def cmd_version(_: argparse.Namespace) -> int:
    print(f"arnis-korea {VERSION}")
    return 0


def cmd_help(args: argparse.Namespace) -> int:
    args.parser.print_help()
    return 0


def add_bbox_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bbox", help="min_lat,min_lng,max_lat,max_lng")
    parser.add_argument("--bbox-file", type=Path)


def add_static_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--level", type=int, default=16)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--scale", type=int, choices=[1, 2], default=2)
    parser.add_argument("--maptype", choices=["basic", "traffic", "satellite", "satellite_base", "terrain"], default="basic")
    parser.add_argument("--format", choices=["jpg", "jpeg", "png8", "png"], default="png")
    parser.add_argument("--dataversion")


def add_secret_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path)
    parser.add_argument("--naver-key-id-file", type=Path)
    parser.add_argument("--naver-key-file", type=Path)


def add_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--mock-raster", type=Path, default=ROOT / "examples" / "mock_raster.ppm")
    parser.add_argument("--mock-width", type=int, default=96)
    parser.add_argument("--mock-height", type=int, default=96)


def parse_optional_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="arnis-korea", description="Generate Korean Minecraft Java worlds with official Naver-only private development support.")
    sub = parser.add_subparsers(dest="command", required=True)

    help_cmd = sub.add_parser("help", help="Print top-level help")
    help_cmd.set_defaults(func=cmd_help, parser=parser)

    generate = sub.add_parser("generate", help="Generate a Minecraft Java world or gated feature output")
    add_bbox_args(generate)
    add_output_args(generate)
    add_static_args(generate)
    add_secret_args(generate)
    generate.add_argument("--source", choices=["osm", "naver-assisted", "naver-only", "mock-naver", "mock", "naver-static"], default="naver-only")
    generate.add_argument("--terrain", type=parse_optional_bool, nargs="?", const=True, default=False, metavar="true|false")
    generate.add_argument("--spawn-lat", type=float)
    generate.add_argument("--spawn-lng", type=float)
    generate.add_argument("--interior", type=parse_optional_bool, default=None, metavar="true|false")
    generate.add_argument("--no-interior", dest="interior", action="store_false")
    generate.add_argument("--roof", type=parse_optional_bool, default=None, metavar="true|false")
    generate.add_argument("--no-roof", dest="roof", action="store_false")
    generate.add_argument("--building-mode", choices=["full", "footprint-only", "roads-terrain", "campus-style"], default="full")
    generate.add_argument("--arnis-scale", type=float)
    generate.add_argument("--arnis-upstream", type=Path, default=ROOT / "upstream" / "arnis")
    generate.add_argument("--allow-static-raster-storage", action="store_true")
    generate.add_argument("--allow-static-raster-analysis", action="store_true")
    generate.add_argument("--accept-naver-static-raster-terms", action="store_true")
    generate.add_argument("--max-static-requests", type=int, default=10)
    generate.add_argument("--world-name", default=DEFAULT_WORLD_NAME)
    generate.add_argument("--minecraft-saves-export", action="store_true")
    generate.add_argument("--clean-world-root", type=parse_optional_bool, default=True, metavar="true|false")
    generate.add_argument("--project-metadata-dir", type=Path)
    generate.add_argument("--keep-debug-in-world-root", type=parse_optional_bool, default=False, metavar="true|false")
    generate.add_argument("--writer", choices=["arnis", "minimal-debug"], default="arnis")
    generate.set_defaults(func=cmd_generate)

    plan = sub.add_parser("plan-static", help="Plan official Naver Static Map raster requests")
    add_bbox_args(plan)
    add_static_args(plan)
    plan.add_argument("--output", type=Path)
    plan.set_defaults(func=cmd_plan_static)

    selector = sub.add_parser("selector", help="Print or initialize the Dynamic Map bbox selector")
    selector.add_argument("--output-bbox", type=Path)
    selector.set_defaults(func=cmd_selector)

    probe = sub.add_parser("probe-naver", help="Call the official Static Map endpoint once without saving the image")
    add_bbox_args(probe)
    add_static_args(probe)
    add_secret_args(probe)
    probe.set_defaults(func=cmd_probe_naver)

    download = sub.add_parser("download-static", help="Download one official Static Map image only when all license gates are explicit")
    add_bbox_args(download)
    add_output_args(download)
    add_static_args(download)
    add_secret_args(download)
    download.add_argument("--output-name", default="static_map_sample.png")
    download.add_argument("--allow-static-raster-storage", action="store_true")
    download.add_argument("--allow-static-raster-analysis", action="store_true")
    download.add_argument("--accept-naver-static-raster-terms", action="store_true")
    download.add_argument("--world-name", default=DEFAULT_WORLD_NAME)
    download.add_argument("--project-metadata-dir", type=Path)
    download.set_defaults(func=cmd_download_static)

    mock = sub.add_parser("mock-vectorize", help="Vectorize the bundled mock raster to normalized features")
    add_bbox_args(mock)
    add_output_args(mock)
    mock.add_argument("--world-name", default=DEFAULT_WORLD_NAME)
    mock.add_argument("--project-metadata-dir", type=Path)
    mock.set_defaults(func=cmd_mock_vectorize)

    export = sub.add_parser("export-features", help="Export normalized Korea feature schema")
    add_bbox_args(export)
    add_output_args(export)
    export.add_argument("--source", choices=["mock", "osm"], default="mock")
    export.add_argument("--world-name", default=DEFAULT_WORLD_NAME)
    export.add_argument("--project-metadata-dir", type=Path)
    export.set_defaults(func=cmd_export_features)

    repair = sub.add_parser("repair-world-layout", help="Copy only Minecraft world files from a mixed folder into a clean world folder")
    repair.add_argument("--input", type=Path, required=True)
    repair.add_argument("--output", type=Path, required=True)
    repair.add_argument("--project-metadata-dir", type=Path)
    repair.add_argument("--overwrite", action="store_true")
    repair.set_defaults(func=cmd_repair_world_layout)

    version = sub.add_parser("version", help="Print version")
    version.set_defaults(func=cmd_version)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
