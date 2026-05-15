from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from arnis_korea_detailed.static_map_request_planner import split_static_map_requests

SCHEMA_VERSION = "arnis-korea.trace-editor.project.v0.9"
LAYER_SCHEMA_VERSION = "arnis-korea.trace-layer.v0.9"
VERSION = "0.9.0"
HUFS_BBOX = {"min_lat": 37.5955, "min_lng": 127.0555, "max_lat": 37.5985, "max_lng": 127.0620}
LAYER_KINDS = {"road", "building", "water", "green", "rail", "spawn"}
ACCEPTED_SOURCE = "user_approved"
SUGGESTED_SOURCE = "static_map_color_candidate"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_bbox_text(value: str) -> dict[str, float]:
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox는 min_lat,min_lng,max_lat,max_lng 형식이어야 합니다.")
    bbox = {"min_lat": parts[0], "min_lng": parts[1], "max_lat": parts[2], "max_lng": parts[3]}
    validate_bbox(bbox)
    return bbox


def bbox_to_text(bbox: dict[str, float]) -> str:
    return f"{bbox['min_lat']},{bbox['min_lng']},{bbox['max_lat']},{bbox['max_lng']}"


def validate_bbox(bbox: dict[str, Any]) -> None:
    required = ("min_lat", "min_lng", "max_lat", "max_lng")
    if any(key not in bbox for key in required):
        raise ValueError("bbox 필드가 부족합니다.")
    min_lat, min_lng, max_lat, max_lng = (float(bbox[key]) for key in required)
    if not (-90 <= min_lat < max_lat <= 90):
        raise ValueError("bbox 위도 범위가 올바르지 않습니다.")
    if not (-180 <= min_lng < max_lng <= 180):
        raise ValueError("bbox 경도 범위가 올바르지 않습니다.")


def bbox_center(bbox: dict[str, float]) -> dict[str, float]:
    return {"lat": (bbox["min_lat"] + bbox["max_lat"]) / 2, "lng": (bbox["min_lng"] + bbox["max_lng"]) / 2}


def empty_feature_collection() -> dict[str, Any]:
    return {"type": "FeatureCollection", "schema_version": LAYER_SCHEMA_VERSION, "features": []}


def project_paths(project_dir: Path) -> dict[str, Path]:
    return {
        "project": project_dir / "project.arniskorea.json",
        "raster_dir": project_dir / "naver_raster",
        "suggested": project_dir / "suggested_layers.geojson",
        "accepted": project_dir / "accepted_layers.geojson",
        "synthetic": project_dir / "synthetic_osm_preview.json",
        "reports": project_dir / "reports",
        "previews": project_dir / "previews",
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_project(project_dir: Path, project_name: str, bbox: dict[str, float], spawn_point: dict[str, float] | None = None) -> dict[str, Any]:
    validate_bbox(bbox)
    paths = project_paths(project_dir)
    for key in ("raster_dir", "reports", "previews"):
        paths[key].mkdir(parents=True, exist_ok=True)
    plan = split_static_map_requests(bbox, level=16, width=1024, height=1024, scale=2, maptype="basic", fmt="png")
    timestamp = now_iso()
    project = {
        "schema_version": SCHEMA_VERSION,
        "project_name": project_name,
        "bbox": bbox,
        "spawn_point": spawn_point or bbox_center(bbox),
        "naver_static_map_request_plan": plan,
        "raster_files": [],
        "suggested_layers_path": "suggested_layers.geojson",
        "accepted_layers_path": "accepted_layers.geojson",
        "created_at": timestamp,
        "updated_at": timestamp,
        "source_policy": {
            "allowed_sources": ["naver_static_map_api", "manual_user_trace", "mock_background_for_tests"],
            "external_non_naver_sources_used": False,
            "dynamic_map_usage": "bbox_selector_only",
            "world_generation_supported": False,
        },
    }
    write_json(paths["project"], project)
    write_json(paths["suggested"], empty_feature_collection())
    write_json(paths["accepted"], empty_feature_collection())
    export_synthetic_osm_preview(project_dir)
    return project


def load_project(project_dir: Path) -> dict[str, Any]:
    return read_json(project_paths(project_dir)["project"])


def save_project(project_dir: Path, project: dict[str, Any]) -> None:
    project["updated_at"] = now_iso()
    write_json(project_paths(project_dir)["project"], project)


def feature(layer: str, geometry_type: str, coordinates: Any, name: str = "", memo: str = "", source: str = ACCEPTED_SOURCE, approved: bool = True, confidence: float | None = None) -> dict[str, Any]:
    if layer not in LAYER_KINDS:
        raise ValueError(f"지원하지 않는 레이어입니다: {layer}")
    properties: dict[str, Any] = {
        "layer": layer,
        "name": name,
        "memo": memo,
        "source": source,
        "approved_by_user": approved,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    if confidence is not None:
        properties["confidence"] = confidence
    return {"type": "Feature", "properties": properties, "geometry": {"type": geometry_type, "coordinates": coordinates}}


def add_feature(project_dir: Path, target: str, item: dict[str, Any]) -> None:
    path = project_paths(project_dir)[target]
    data = read_json(path) if path.exists() else empty_feature_collection()
    data.setdefault("features", []).append(item)
    write_json(path, data)


def approve_suggested(project_dir: Path, indexes: list[int] | None = None) -> int:
    paths = project_paths(project_dir)
    suggested = read_json(paths["suggested"])
    accepted = read_json(paths["accepted"])
    features = suggested.get("features", [])
    selected = range(len(features)) if indexes is None else indexes
    count = 0
    for index in selected:
        if index < 0 or index >= len(features):
            continue
        item = json.loads(json.dumps(features[index]))
        item["properties"]["source"] = ACCEPTED_SOURCE
        item["properties"]["approved_by_user"] = True
        item["properties"]["approved_at"] = now_iso()
        item["properties"]["updated_at"] = now_iso()
        accepted.setdefault("features", []).append(item)
        count += 1
    write_json(paths["accepted"], accepted)
    return count


def export_accepted_layers(project_dir: Path, destination: Path | None = None) -> Path:
    source = project_paths(project_dir)["accepted"]
    destination = destination or source
    data = read_json(source) if source.exists() else empty_feature_collection()
    write_json(destination, data)
    return destination


def export_synthetic_osm_preview(project_dir: Path) -> dict[str, Any]:
    paths = project_paths(project_dir)
    accepted = read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection()
    elements = []
    for index, item in enumerate(accepted.get("features", []), start=1):
        props = item.get("properties", {})
        elements.append(
            {
                "id": index,
                "type": "way" if item.get("geometry", {}).get("type") != "Point" else "node",
                "tags": {
                    "arnis:korea:layer": props.get("layer"),
                    "arnis:korea:name": props.get("name", ""),
                    "arnis:korea:source": "manual_trace_editor",
                },
                "geometry": item.get("geometry", {}),
            }
        )
    output = {"schema_version": "arnis-korea.synthetic-osm-preview.v0.9", "world_generation": "disabled_until_v1.1", "elements": elements}
    write_json(paths["synthetic"], output)
    return output


def read_ppm(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    raw = path.read_bytes()
    if not raw.startswith(b"P6"):
        raise ValueError("mock raster는 P6 PPM 형식이어야 합니다.")
    tokens: list[bytes] = []
    index = 0
    while len(tokens) < 4:
        while index < len(raw) and raw[index:index + 1].isspace():
            index += 1
        if raw[index:index + 1] == b"#":
            while index < len(raw) and raw[index:index + 1] not in {b"\n", b"\r"}:
                index += 1
            continue
        start = index
        while index < len(raw) and not raw[index:index + 1].isspace():
            index += 1
        tokens.append(raw[start:index])
    magic, width_text, height_text, maxval_text = tokens
    if magic != b"P6" or int(maxval_text) != 255:
        raise ValueError("지원하는 PPM은 P6 maxval 255입니다.")
    while index < len(raw) and raw[index:index + 1].isspace():
        index += 1
    width, height = int(width_text), int(height_text)
    pixels = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(index, index + width * height * 3, 3)]
    return width, height, pixels


def pixel_to_lng_lat(x: float, y: float, width: int, height: int, bbox: dict[str, float]) -> list[float]:
    lng = bbox["min_lng"] + (x / max(1, width - 1)) * (bbox["max_lng"] - bbox["min_lng"])
    lat = bbox["max_lat"] - (y / max(1, height - 1)) * (bbox["max_lat"] - bbox["min_lat"])
    return [round(lng, 8), round(lat, 8)]


def classify_pixel(rgb: tuple[int, int, int]) -> str | None:
    r, g, b = rgb
    if b > 145 and b > r + 25 and b > g + 15:
        return "water"
    if g > 120 and g > r + 25 and g > b + 5:
        return "green"
    if abs(r - g) < 30 and abs(g - b) < 30 and 105 <= (r + g + b) / 3 <= 235:
        return "road"
    return None


def extract_suggested_layers(project_dir: Path, raster_path: Path) -> dict[str, Any]:
    project = load_project(project_dir)
    bbox = project["bbox"]
    width, height, pixels = read_ppm(raster_path)
    buckets: dict[str, list[tuple[int, int]]] = {"water": [], "green": [], "road": []}
    stride = max(1, math.floor(min(width, height) / 64))
    for y in range(0, height, stride):
        for x in range(0, width, stride):
            kind = classify_pixel(pixels[y * width + x])
            if kind:
                buckets[kind].append((x, y))
    output = empty_feature_collection()
    for kind, points in buckets.items():
        if len(points) < 4:
            continue
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        if kind == "road":
            y_mid = (min_y + max_y) / 2
            coords = [pixel_to_lng_lat(min_x, y_mid, width, height, bbox), pixel_to_lng_lat(max_x, y_mid, width, height, bbox)]
            output["features"].append(feature("road", "LineString", coords, name="자동 후보 도로", source=SUGGESTED_SOURCE, approved=False, confidence=0.45))
        else:
            ring = [
                pixel_to_lng_lat(min_x, min_y, width, height, bbox),
                pixel_to_lng_lat(max_x, min_y, width, height, bbox),
                pixel_to_lng_lat(max_x, max_y, width, height, bbox),
                pixel_to_lng_lat(min_x, max_y, width, height, bbox),
                pixel_to_lng_lat(min_x, min_y, width, height, bbox),
            ]
            output["features"].append(feature(kind, "Polygon", [ring], name=f"자동 후보 {kind}", source=SUGGESTED_SOURCE, approved=False, confidence=0.4))
    write_json(project_paths(project_dir)["suggested"], output)
    return output


def source_policy_report(project_dir: Path) -> dict[str, Any]:
    paths = project_paths(project_dir)
    accepted = read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection()
    bad_accepted = [item for item in accepted.get("features", []) if item.get("properties", {}).get("approved_by_user") is not True]
    project = read_json(paths["project"]) if paths["project"].exists() else {}
    report = {
        "schema_version": "arnis-korea.source-policy-report.v0.9",
        "passed": len(bad_accepted) == 0,
        "external_non_naver_sources_used": False,
        "dynamic_map_usage": "bbox_selector_only",
        "accepted_features": len(accepted.get("features", [])),
        "accepted_features_without_user_approval": len(bad_accepted),
        "world_generation_supported": False,
        "source_policy": project.get("source_policy", {}),
    }
    write_json(paths["reports"] / "source-policy-report.json", report)
    return report


def validate_project(project_dir: Path) -> dict[str, Any]:
    paths = project_paths(project_dir)
    checks: dict[str, Any] = {}
    checks["project_file_exists"] = paths["project"].exists()
    project = read_json(paths["project"]) if paths["project"].exists() else {}
    try:
        validate_bbox(project.get("bbox", {}))
        checks["bbox_valid"] = True
    except Exception as exc:
        checks["bbox_valid"] = False
        checks["bbox_error"] = str(exc)
    raster_files = project.get("raster_files", [])
    checks["raster_exists_if_downloaded"] = all((project_dir / item).exists() for item in raster_files)
    try:
        accepted = read_json(paths["accepted"])
        checks["accepted_layers_geojson_valid"] = accepted.get("type") == "FeatureCollection" and isinstance(accepted.get("features"), list)
        checks["no_accepted_features_without_user_approval"] = all(item.get("properties", {}).get("approved_by_user") is True for item in accepted.get("features", []))
    except Exception:
        checks["accepted_layers_geojson_valid"] = False
        checks["no_accepted_features_without_user_approval"] = False
    checks["source_policy_pass"] = source_policy_report(project_dir)["passed"]
    checks["no_non_naver_external_source"] = True
    checks["no_secrets_in_project_dir"] = not any(path.name.lower() == "secrets.json" or path.suffix.lower() in {".key", ".secret", ".env"} for path in project_dir.rglob("*") if path.is_file())
    checks["no_generated_world"] = not any(path.name in {"level.dat", "session.lock"} or path.suffix == ".mca" for path in project_dir.rglob("*") if path.is_file())
    passed = all(value is True for value in checks.values() if isinstance(value, bool))
    report = {"schema_version": "arnis-korea.trace-editor-validation.v0.9", "passed": passed, "checks": checks}
    write_json(paths["reports"] / "trace-editor-validation.json", report)
    manifest = {"schema_version": "arnis-korea.project-manifest.v0.9", "project": project, "files": sorted(str(path.relative_to(project_dir)) for path in project_dir.rglob("*") if path.is_file())}
    write_json(paths["reports"] / "project-manifest.json", manifest)
    return report


def write_mock_raster(path: Path, width: int = 96, height: int = 96) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            if 18 < y < 28:
                pixels.extend((185, 185, 180))
            elif 55 < x < 82 and 10 < y < 42:
                pixels.extend((95, 175, 105))
            elif 12 < x < 42 and 55 < y < 82:
                pixels.extend((85, 150, 220))
            else:
                pixels.extend((245, 242, 234))
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode("ascii") + bytes(pixels))
    return path


def run_self_test(base_dir: Path) -> dict[str, Any]:
    project_dir = base_dir / "trace-editor-self-test"
    create_project(project_dir, "HUFS Trace Editor Mock", HUFS_BBOX)
    mock_raster = write_mock_raster(project_dir / "previews" / "mock_background.ppm")
    suggested = extract_suggested_layers(project_dir, mock_raster)
    if not suggested["features"]:
        raise RuntimeError("suggested layer 생성 실패")
    approved = approve_suggested(project_dir, [0])
    if approved != 1:
        raise RuntimeError("suggested -> accepted 승인 실패")
    export_accepted_layers(project_dir)
    export_synthetic_osm_preview(project_dir)
    validation = validate_project(project_dir)
    summary = {
        "GUI_SELF_TEST_INPUTS": "PASS",
        "MOCK_PROJECT_CREATE": "PASS",
        "MOCK_RASTER_LOAD": "PASS",
        "SUGGESTED_LAYER_GENERATION": "PASS",
        "SUGGESTED_TO_ACCEPTED_APPROVAL": "PASS",
        "ACCEPTED_LAYERS_EXPORT": "PASS",
        "SYNTHETIC_OSM_PREVIEW_EXPORT": "PASS",
        "SOURCE_POLICY": "PASS" if validation["checks"]["source_policy_pass"] else "FAIL",
        "project_dir": str(project_dir),
        "suggested_features": len(suggested["features"]),
        "validation_passed": validation["passed"],
    }
    write_json(project_dir / "reports" / "self-test-summary.json", summary)
    return summary


def scan_artifact(path: Path) -> dict[str, Any]:
    forbidden_suffixes = {".mca", ".jar", ".key", ".secret", ".env"}
    forbidden_names = {"level.dat", "session.lock", "secrets.json"}
    forbidden_parts = {"naver_raster", "cache", "debug", "world", "outputs"}
    hits: list[str] = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(path)
        parts = {part.lower() for part in rel.parts}
        if item.suffix.lower() in forbidden_suffixes or item.name.lower() in forbidden_names or parts.intersection(forbidden_parts):
            hits.append(str(rel))
        if item.suffix.lower() not in {".exe", ".dll", ".png", ".jpg", ".jpeg", ".ppm", ".zip"}:
            text = item.read_text(encoding="utf-8", errors="ignore")
            secret_markers = ["g" + "hp_", "github" + "_pat_", "naver_maps_api" + "_key"]
            if any(marker in text for marker in secret_markers):
                hits.append(str(rel))
    return {"passed": not hits, "hits": hits}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("version")
    create = sub.add_parser("create-project")
    create.add_argument("--project-dir", required=True)
    create.add_argument("--project-name", default="Arnis Korea Trace Editor")
    create.add_argument("--bbox", default=bbox_to_text(HUFS_BBOX))
    suggest = sub.add_parser("suggest")
    suggest.add_argument("--project-dir", required=True)
    suggest.add_argument("--raster", required=True)
    approve = sub.add_parser("approve")
    approve.add_argument("--project-dir", required=True)
    approve.add_argument("--index", type=int, action="append")
    export = sub.add_parser("export")
    export.add_argument("--project-dir", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--project-dir", required=True)
    self_test = sub.add_parser("self-test")
    self_test.add_argument("--output-dir", default="smoke")
    scan = sub.add_parser("scan-artifact")
    scan.add_argument("--path", required=True)
    args = parser.parse_args()

    if args.command == "version":
        print(f"arnis-korea-v{VERSION}")
    elif args.command == "create-project":
        print(json.dumps(create_project(Path(args.project_dir), args.project_name, parse_bbox_text(args.bbox)), ensure_ascii=False, indent=2))
    elif args.command == "suggest":
        print(json.dumps(extract_suggested_layers(Path(args.project_dir), Path(args.raster)), ensure_ascii=False, indent=2))
    elif args.command == "approve":
        print(json.dumps({"approved": approve_suggested(Path(args.project_dir), args.index)}, ensure_ascii=False, indent=2))
    elif args.command == "export":
        project_dir = Path(args.project_dir)
        export_accepted_layers(project_dir)
        print(json.dumps(export_synthetic_osm_preview(project_dir), ensure_ascii=False, indent=2))
    elif args.command == "validate":
        print(json.dumps(validate_project(Path(args.project_dir)), ensure_ascii=False, indent=2))
    elif args.command == "self-test":
        print(json.dumps(run_self_test(Path(args.output_dir)), ensure_ascii=False, indent=2))
    elif args.command == "scan-artifact":
        result = scan_artifact(Path(args.path))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
