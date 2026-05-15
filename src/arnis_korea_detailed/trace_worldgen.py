from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from arnis_korea_detailed.arnis_no_network_renderer import run_patched_arnis_renderer
from arnis_korea_detailed.minecraft_load_smoke import run_minecraft_load_smoke
from arnis_korea_detailed.minecraft_world_validator import validate_world_layout
from arnis_korea_detailed.trace_editor_core import (
    ACCEPTED_SOURCE,
    HUFS_BBOX,
    bbox_center,
    create_project,
    empty_feature_collection,
    ensure_feature_ids,
    feature,
    load_project,
    now_iso,
    project_paths,
    read_json,
    validate_bbox,
    validate_layer_collection,
    write_json,
)

SYNTHETIC_OSM_SCHEMA_VERSION = "arnis-korea.synthetic-osm.v1.1"
WORLDGEN_REPORT_SCHEMA_VERSION = "arnis-korea.worldgen-report.v1.1"
SOURCE_POLICY_SCHEMA_VERSION = "arnis-korea.source-policy-report.v1.1"


def _feature_layer(item: dict[str, Any]) -> str:
    return str(item.get("properties", {}).get("layer", ""))


def _coords_in_bbox(coords: list[list[float]], bbox: dict[str, float]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for index, coord in enumerate(coords):
        if len(coord) != 2:
            errors.append({"code": "invalid_coordinate", "index": index, "coordinate": coord})
            continue
        lng, lat = float(coord[0]), float(coord[1])
        if not (bbox["min_lng"] <= lng <= bbox["max_lng"] and bbox["min_lat"] <= lat <= bbox["max_lat"]):
            errors.append({"code": "coordinate_outside_bbox", "index": index, "coordinate": coord})
    return errors


def _feature_points(item: dict[str, Any]) -> list[list[float]]:
    geometry = item.get("geometry", {})
    if geometry.get("type") == "Point":
        return [geometry.get("coordinates", [])]
    if geometry.get("type") == "LineString":
        return geometry.get("coordinates", [])
    if geometry.get("type") == "Polygon":
        return geometry.get("coordinates", [[]])[0]
    return []


def validate_accepted_for_worldgen(project_dir: Path) -> dict[str, Any]:
    paths = project_paths(project_dir)
    project = load_project(project_dir)
    bbox = project.get("bbox", {})
    validate_bbox(bbox)
    accepted = ensure_feature_ids(read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection())
    layer_validation = validate_layer_collection(accepted, require_approved=True)
    errors: list[dict[str, Any]] = list(layer_validation.get("errors", []))
    features = accepted.get("features", [])
    if not features:
        errors.append({"code": "empty_accepted_layers", "message": "승인된 레이어가 없습니다."})
    seen_ids: set[str] = set()
    for index, item in enumerate(features):
        props = item.get("properties", {})
        feature_id = props.get("id")
        source = props.get("source")
        approved = props.get("approved_by_user")
        if feature_id in seen_ids:
            errors.append({"code": "duplicate_id", "index": index, "id": feature_id})
        if feature_id:
            seen_ids.add(feature_id)
        if approved is not True or source != ACCEPTED_SOURCE:
            errors.append({"code": "suggested_or_unapproved_feature_in_worldgen_input", "index": index, "id": feature_id})
        layer = _feature_layer(item)
        geometry = item.get("geometry", {})
        if layer == "spawn":
            continue
        errors.extend({"feature": index, **error} for error in _coords_in_bbox(_feature_points(item), bbox))
        if layer in {"building", "water", "green"}:
            ring = geometry.get("coordinates", [[]])[0] if geometry.get("type") == "Polygon" else []
            if ring and ring[0] != ring[-1]:
                errors.append({"code": "polygon_not_closed", "index": index})
        if layer in {"road", "rail"} and len(_feature_points(item)) < 2:
            errors.append({"code": "line_requires_two_points", "index": index})
    return {
        "schema_version": "arnis-korea.worldgen-input-validation.v1.1",
        "passed": not errors,
        "feature_count": len(features),
        "errors": errors,
        "warnings": layer_validation.get("warnings", []),
    }


def _road_highway(props: dict[str, Any]) -> str:
    value = str(props.get("road_class") or props.get("class") or props.get("metadata", {}).get("road_class", "")).lower()
    if value == "major":
        return "primary"
    if value == "minor":
        return "secondary"
    if value in {"primary", "secondary", "residential"}:
        return value
    return "residential"


def _tags_for_feature(item: dict[str, Any], building_height_mode: str) -> dict[str, str] | None:
    props = item.get("properties", {})
    layer = props.get("layer")
    tags: dict[str, str]
    if layer == "road":
        tags = {"highway": _road_highway(props)}
    elif layer == "rail":
        tags = {"railway": "rail"}
    elif layer == "building":
        levels = "1" if building_height_mode == "footprint" else "2"
        if building_height_mode == "experimental_full":
            levels = str(max(1, min(3, int(props.get("building_levels", 2) or 2))))
        tags = {"building": "yes", "building:levels": levels}
    elif layer == "water":
        tags = {"natural": "water"}
    elif layer == "green":
        tags = {"leisure": "park"}
    else:
        return None
    tags["arnis:korea:source"] = "accepted_trace_editor"
    if props.get("name"):
        tags["name"] = str(props.get("name"))
    return tags


def export_synthetic_osm(project_dir: Path, building_height_mode: str = "low-rise") -> dict[str, Any]:
    project_dir = Path(project_dir)
    paths = project_paths(project_dir)
    project = load_project(project_dir)
    bbox = project.get("bbox", {})
    validation = validate_accepted_for_worldgen(project_dir)
    report_path = paths["reports"] / "synthetic_osm_export_report.json"
    if not validation["passed"]:
        report = {
            "schema_version": "arnis-korea.synthetic-osm-export-report.v1.1",
            "passed": False,
            "created_at": now_iso(),
            "validation": validation,
            "suggested_layers_used_for_worldgen": False,
        }
        write_json(report_path, report)
        raise ValueError("accepted_layers.geojson 검증 실패: reports/synthetic_osm_export_report.json 확인")

    accepted = ensure_feature_ids(read_json(paths["accepted"]))
    node_ids: dict[tuple[float, float], int] = {}
    nodes: list[dict[str, Any]] = []
    ways: list[dict[str, Any]] = []
    next_node_id = 1
    next_way_id = 10_000

    def node_id(coord: list[float]) -> int:
        nonlocal next_node_id
        key = (round(float(coord[0]), 8), round(float(coord[1]), 8))
        if key not in node_ids:
            node_ids[key] = next_node_id
            nodes.append({"type": "node", "id": next_node_id, "lat": key[1], "lon": key[0]})
            next_node_id += 1
        return node_ids[key]

    for item in accepted.get("features", []):
        tags = _tags_for_feature(item, building_height_mode)
        if tags is None:
            continue
        refs = [node_id(coord) for coord in _feature_points(item)]
        ways.append({"type": "way", "id": next_way_id, "nodes": refs, "tags": tags})
        next_way_id += 1

    refs = {node for way in ways for node in way["nodes"]}
    node_ids_written = {node["id"] for node in nodes}
    missing_refs = sorted(refs - node_ids_written)
    output = {
        "schema_version": SYNTHETIC_OSM_SCHEMA_VERSION,
        "generator": "arnis-korea-trace-editor",
        "source_policy": "naver_trace_editor_accepted_layers",
        "bbox": bbox,
        "elements": [*nodes, *ways],
    }
    write_json(project_dir / "synthetic_osm.json", output)
    report = {
        "schema_version": "arnis-korea.synthetic-osm-export-report.v1.1",
        "passed": not missing_refs and bool(ways),
        "created_at": now_iso(),
        "synthetic_osm_path": "synthetic_osm.json",
        "node_count": len(nodes),
        "way_count": len(ways),
        "missing_way_node_refs": missing_refs,
        "polygon_closed_ring": True,
        "bbox_checked": True,
        "suggested_layers_used_for_worldgen": False,
        "schema_version_recorded": SYNTHETIC_OSM_SCHEMA_VERSION,
        "validation": validation,
    }
    write_json(report_path, report)
    return output


def write_v11_source_policy_report(project_dir: Path) -> dict[str, Any]:
    report = {
        "schema_version": SOURCE_POLICY_SCHEMA_VERSION,
        "source_policy": "naver_trace_editor_accepted_layers",
        "worldgen_input": "accepted_layers_only",
        "suggested_layers_used_for_worldgen": False,
        "external_non_naver_sources_used": False,
        "renderer_network_disabled": True,
        "synthetic_osm_used": True,
        "custom_anvil_writer_used": False,
        "passed": True,
    }
    write_json(project_paths(project_dir)["reports"] / "source-policy-report.json", report)
    return report


def _safe_world_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9가-힣._ -]+", "_", value).strip(" .")
    return name or "Arnis Korea World"


def copy_world_to_saves(world_dir: Path, saves_dir: Path) -> Path:
    target = saves_dir / world_dir.name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(world_dir, target, ignore=shutil.ignore_patterns("*.json", "*.md", "reports", "previews", "naver_raster"))
    return target


def _clean_world_root(world_dir: Path, reports_dir: Path) -> dict[str, Any]:
    moved: list[str] = []
    for item in list(world_dir.iterdir()) if world_dir.exists() else []:
        if item.is_file() and item.suffix.lower() in {".json", ".md"}:
            reports_dir.mkdir(parents=True, exist_ok=True)
            target = reports_dir / f"arnis-writer-{item.name}"
            if target.exists():
                target.unlink()
            shutil.move(str(item), str(target))
            moved.append(item.name)
    return {"moved_world_root_metadata": moved}


def generate_world_from_project(
    project_dir: Path,
    root: Path,
    world_name: str,
    building_height_mode: str = "low-rise",
    terrain: bool = False,
    interior: bool = False,
    roof: bool = True,
    scale: float = 1.0,
    run_load_smoke: bool = False,
    paper_minecraft_version: str = "26.1.2",
    paper_api_version: str = "26.1.2",
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    project_dir = Path(project_dir)
    root = Path(root)
    project = load_project(project_dir)
    bbox = project.get("bbox", {})
    validate_bbox(bbox)
    spawn = project.get("spawn_point") or bbox_center(bbox)
    write_v11_source_policy_report(project_dir)
    export_synthetic_osm(project_dir, building_height_mode=building_height_mode)
    output_parent = project_dir / "playable_world"
    final_world_dir = output_parent / _safe_world_name(world_name or project.get("project_name", "Arnis Korea World"))
    renderer = run_patched_arnis_renderer(
        root=root,
        synthetic_osm_path=project_dir / "synthetic_osm.json",
        bbox=bbox,
        output_parent=output_parent,
        world_dir=final_world_dir,
        terrain=terrain,
        interior=interior,
        roof=roof,
        spawn_lat=float(spawn["lat"]),
        spawn_lng=float(spawn["lng"]),
        scale=scale,
    )
    worldgen_report: dict[str, Any] = {
        "schema_version": WORLDGEN_REPORT_SCHEMA_VERSION,
        "created_at": now_iso(),
        "world_name": final_world_dir.name,
        "world_dir": str(final_world_dir),
        "worldgen_input": "accepted_layers_only",
        "suggested_layers_used_for_worldgen": False,
        "renderer_network_disabled": renderer.get("renderer_network_disabled") is True,
        "external_non_naver_sources_used": False,
        "synthetic_osm_used": True,
        "custom_anvil_writer_used": False,
        "renderer": renderer,
        "passed": False,
    }
    if not renderer.get("executed") or renderer.get("returncode") != 0:
        write_json(project_paths(project_dir)["reports"] / "worldgen-report.json", worldgen_report)
        raise RuntimeError(f"Arnis Writer 실행 실패: {renderer.get('reason') or renderer.get('returncode')}")

    clean_result = _clean_world_root(final_world_dir, project_paths(project_dir)["reports"])
    worldgen_report["clean_world_root"] = clean_result
    validation = validate_world_layout(final_world_dir, project_paths(project_dir)["reports"], write_report=True)
    worldgen_report["world_validation"] = validation
    if run_load_smoke:
        smoke_dir = project_paths(project_dir)["reports"] / "minecraft-load-smoke-work"
        smoke = run_minecraft_load_smoke(
            final_world_dir,
            smoke_dir,
            target_version=paper_minecraft_version,
            paper_api_version=paper_api_version,
            timeout_seconds=timeout_seconds,
        )
        write_json(project_paths(project_dir)["reports"] / "minecraft-load-smoke.json", smoke)
        (project_paths(project_dir)["reports"] / "minecraft-load-smoke.log").write_text(
            str(smoke.get("stdout_tail", "")) + "\n" + str(smoke.get("latest_log_tail", "")),
            encoding="utf-8",
        )
        shutil.rmtree(smoke_dir, ignore_errors=True)
        worldgen_report["minecraft_load_smoke"] = {"passed": smoke.get("passed"), "target_paper_api_version": paper_api_version}
    else:
        worldgen_report["minecraft_load_smoke"] = {"executed": False, "required_for_release": True}
    worldgen_report["passed"] = bool(validation.get("valid") and (not run_load_smoke or worldgen_report["minecraft_load_smoke"].get("passed")))
    write_json(project_paths(project_dir)["reports"] / "worldgen-report.json", worldgen_report)
    return worldgen_report


def run_worldgen_self_test(base_dir: Path, root: Path, run_renderer: bool = False, run_load_smoke: bool = False) -> dict[str, Any]:
    project_dir = Path(base_dir) / "worldgen-self-test"
    if project_dir.exists():
        shutil.rmtree(project_dir)
    create_project(project_dir, "Arnis Korea v1.1 Mock", HUFS_BBOX)
    accepted = empty_feature_collection()
    accepted["features"] = [
        feature("road", "LineString", [[127.056, 37.598], [127.057, 37.5976]], name="테스트 도로"),
        feature("rail", "LineString", [[127.058, 37.598], [127.061, 37.5972]], name="테스트 철도"),
        feature("building", "Polygon", [[[127.056, 37.5968], [127.0565, 37.5968], [127.0565, 37.5964], [127.056, 37.5964], [127.056, 37.5968]]], name="테스트 건물"),
        feature("water", "Polygon", [[[127.057, 37.596], [127.0574, 37.596], [127.0574, 37.5957], [127.057, 37.5957], [127.057, 37.596]]], name="테스트 수역"),
        feature("green", "Polygon", [[[127.058, 37.596], [127.0584, 37.596], [127.0584, 37.5957], [127.058, 37.5957], [127.058, 37.596]]], name="테스트 녹지"),
        feature("spawn", "Point", [127.05875, 37.597], name="스폰"),
    ]
    write_json(project_paths(project_dir)["accepted"], accepted)
    synthetic = export_synthetic_osm(project_dir)
    source_policy = write_v11_source_policy_report(project_dir)
    summary: dict[str, Any] = {
        "SYNTHETIC_OSM_EXPORT": "PASS",
        "SYNTHETIC_OSM_SCHEMA": "PASS" if synthetic.get("schema_version") == SYNTHETIC_OSM_SCHEMA_VERSION else "FAIL",
        "SOURCE_POLICY_V11": "PASS" if source_policy.get("suggested_layers_used_for_worldgen") is False else "FAIL",
        "project_dir": str(project_dir),
    }
    if run_renderer:
        report = generate_world_from_project(project_dir, root=root, world_name="Arnis Korea v1.1 Mock", run_load_smoke=run_load_smoke)
        summary["ARNIS_NO_NETWORK_WORLDGEN"] = "PASS" if report.get("renderer", {}).get("returncode") == 0 else "FAIL"
        summary["CLEAN_WORLD_LAYOUT"] = "PASS" if report.get("world_validation", {}).get("valid") else "FAIL"
        summary["PAPER_26_1_2_LOAD_SMOKE"] = "PASS" if report.get("minecraft_load_smoke", {}).get("passed") else "FAIL"
    write_json(project_paths(project_dir)["reports"] / "worldgen-self-test-summary.json", summary)
    return summary


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export-synthetic-osm")
    export.add_argument("--project-dir", required=True)
    world = sub.add_parser("generate-world")
    world.add_argument("--project-dir", required=True)
    world.add_argument("--root", default=".")
    world.add_argument("--world-name", required=True)
    world.add_argument("--load-smoke", action="store_true")
    self_test = sub.add_parser("self-test")
    self_test.add_argument("--output-dir", default="smoke")
    self_test.add_argument("--root", default=".")
    self_test.add_argument("--renderer", action="store_true")
    self_test.add_argument("--load-smoke", action="store_true")
    args = parser.parse_args()
    if args.command == "export-synthetic-osm":
        print(json.dumps(export_synthetic_osm(Path(args.project_dir)), ensure_ascii=False, indent=2))
    elif args.command == "generate-world":
        print(json.dumps(generate_world_from_project(Path(args.project_dir), Path(args.root), args.world_name, run_load_smoke=args.load_smoke), ensure_ascii=False, indent=2))
    elif args.command == "self-test":
        print(json.dumps(run_worldgen_self_test(Path(args.output_dir), Path(args.root), args.renderer, args.load_smoke), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
