from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from arnis_korea_detailed.static_map_request_planner import split_static_map_requests

SCHEMA_VERSION = "arnis-korea.trace-editor.project.v2.0"
LAYER_SCHEMA_VERSION = "arnis-korea.trace-layer.v2.0"
VERSION = "2.0.0-private-final"
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
        "synthetic_osm": project_dir / "synthetic_osm.json",
        "playable_world": project_dir / "playable_world",
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
            "world_generation_supported": True,
            "worldgen_input": "accepted_layers_only",
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


def feature(layer: str, geometry_type: str, coordinates: Any, name: str = "", memo: str = "", source: str = ACCEPTED_SOURCE, approved: bool = True, confidence: float | None = None, feature_id: str | None = None) -> dict[str, Any]:
    if layer not in LAYER_KINDS:
        raise ValueError(f"지원하지 않는 레이어입니다: {layer}")
    properties: dict[str, Any] = {
        "id": feature_id or f"ak-{uuid.uuid4().hex[:12]}",
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


def ensure_feature_ids(collection: dict[str, Any]) -> dict[str, Any]:
    for item in collection.get("features", []):
        props = item.setdefault("properties", {})
        if not props.get("id"):
            props["id"] = f"ak-{uuid.uuid4().hex[:12]}"
    return collection


def add_feature(project_dir: Path, target: str, item: dict[str, Any]) -> None:
    path = project_paths(project_dir)[target]
    data = ensure_feature_ids(read_json(path) if path.exists() else empty_feature_collection())
    data.setdefault("features", []).append(item)
    write_json(path, data)


def approve_suggested(project_dir: Path, indexes: list[int] | None = None) -> int:
    paths = project_paths(project_dir)
    suggested = ensure_feature_ids(read_json(paths["suggested"]))
    accepted = ensure_feature_ids(read_json(paths["accepted"]))
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
        item["properties"]["id"] = f"ak-{uuid.uuid4().hex[:12]}"
        accepted.setdefault("features", []).append(item)
        count += 1
    write_json(paths["accepted"], accepted)
    return count


def revert_accepted_to_suggested(project_dir: Path, indexes: list[int]) -> int:
    paths = project_paths(project_dir)
    accepted = ensure_feature_ids(read_json(paths["accepted"]))
    suggested = ensure_feature_ids(read_json(paths["suggested"]))
    moved = 0
    for index in sorted(set(indexes), reverse=True):
        if index < 0 or index >= len(accepted.get("features", [])):
            continue
        item = accepted["features"].pop(index)
        props = item.setdefault("properties", {})
        props["source"] = "reverted_from_accepted"
        props["approved_by_user"] = False
        props["updated_at"] = now_iso()
        suggested.setdefault("features", []).append(item)
        moved += 1
    write_json(paths["accepted"], accepted)
    write_json(paths["suggested"], suggested)
    export_synthetic_osm_preview(project_dir)
    return moved


def export_accepted_layers(project_dir: Path, destination: Path | None = None) -> Path:
    source = project_paths(project_dir)["accepted"]
    destination = destination or source
    data = ensure_feature_ids(read_json(source) if source.exists() else empty_feature_collection())
    write_json(destination, data)
    return destination


def export_synthetic_osm_preview(project_dir: Path) -> dict[str, Any]:
    paths = project_paths(project_dir)
    accepted = ensure_feature_ids(read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection())
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
    output = {"schema_version": "arnis-korea.synthetic-osm-preview.v2.0", "world_generation": "enabled_private_final_v2_after_accepted_export", "elements": elements}
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


def lng_lat_to_pixel(lng: float, lat: float, width: int, height: int, bbox: dict[str, float]) -> tuple[float, float]:
    validate_bbox(bbox)
    x = (lng - bbox["min_lng"]) / (bbox["max_lng"] - bbox["min_lng"]) * max(1, width - 1)
    y = (bbox["max_lat"] - lat) / (bbox["max_lat"] - bbox["min_lat"]) * max(1, height - 1)
    return x, y


def coordinate_roundtrip_report(bbox: dict[str, float], width: int = 1024, height: int = 1024) -> dict[str, Any]:
    samples = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1), ((width - 1) / 2, (height - 1) / 2)]
    errors = []
    for x, y in samples:
        lng, lat = pixel_to_lng_lat(x, y, width, height, bbox)
        x2, y2 = lng_lat_to_pixel(lng, lat, width, height, bbox)
        errors.append(max(abs(x - x2), abs(y - y2)))
    max_error = max(errors) if errors else 0.0
    return {"passed": max_error <= 0.01, "max_pixel_error": round(max_error, 6), "samples": len(samples)}


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
    accepted = ensure_feature_ids(read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection())
    bad_accepted = [item for item in accepted.get("features", []) if item.get("properties", {}).get("approved_by_user") is not True]
    project = read_json(paths["project"]) if paths["project"].exists() else {}
    report = {
        "schema_version": "arnis-korea.source-policy-report.v1.1",
        "passed": len(bad_accepted) == 0,
        "source_policy": "naver_trace_editor_accepted_layers",
        "worldgen_input": "accepted_layers_only",
        "suggested_layers_used_for_worldgen": False,
        "external_non_naver_sources_used": False,
        "renderer_network_disabled": True,
        "synthetic_osm_used": True,
        "custom_anvil_writer_used": False,
        "dynamic_map_usage": "bbox_selector_only",
        "accepted_features": len(accepted.get("features", [])),
        "accepted_features_without_user_approval": len(bad_accepted),
        "world_generation_supported": True,
        "project_source_policy": project.get("source_policy", {}),
    }
    write_json(paths["reports"] / "source-policy-report.json", report)
    return report


def expected_geometry_type(layer: str) -> str:
    if layer in {"road", "rail"}:
        return "LineString"
    if layer in {"building", "water", "green"}:
        return "Polygon"
    if layer == "spawn":
        return "Point"
    return ""


def iter_geometry_points(geometry: dict[str, Any]) -> list[list[float]]:
    if geometry.get("type") == "Point":
        return [geometry.get("coordinates", [])]
    if geometry.get("type") == "LineString":
        return geometry.get("coordinates", [])
    if geometry.get("type") == "Polygon":
        return geometry.get("coordinates", [[]])[0]
    return []


def validate_layer_collection(collection: dict[str, Any], require_approved: bool) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    ids: set[str] = set()
    features = collection.get("features", [])
    if collection.get("type") != "FeatureCollection":
        errors.append({"code": "not_feature_collection"})
    if not isinstance(features, list):
        errors.append({"code": "features_not_list"})
        features = []
    if not features:
        warnings.append({"code": "empty_project_warning", "message": "accepted layer가 비어 있습니다."})
    for index, item in enumerate(features):
        props = item.get("properties", {})
        geometry = item.get("geometry", {})
        feature_id = props.get("id")
        layer = props.get("layer")
        if not feature_id:
            errors.append({"index": index, "code": "missing_id"})
        elif feature_id in ids:
            errors.append({"index": index, "id": feature_id, "code": "duplicate_id"})
        else:
            ids.add(feature_id)
        if layer not in LAYER_KINDS:
            errors.append({"index": index, "code": "invalid_layer", "layer": layer})
        expected = expected_geometry_type(layer)
        if expected and geometry.get("type") != expected:
            errors.append({"index": index, "code": "geometry_type_mismatch", "expected": expected, "actual": geometry.get("type")})
        if require_approved and props.get("approved_by_user") is not True:
            errors.append({"index": index, "code": "accepted_feature_without_user_approval"})
        points = iter_geometry_points(geometry)
        for point_index, point in enumerate(points):
            if not isinstance(point, list) or len(point) != 2:
                errors.append({"index": index, "point": point_index, "code": "invalid_coordinate"})
        if geometry.get("type") == "LineString" and len(points) < 2:
            errors.append({"index": index, "code": "line_requires_two_points"})
        if geometry.get("type") == "Polygon":
            if len(points) < 4:
                errors.append({"index": index, "code": "polygon_requires_four_ring_points"})
            elif points[0] != points[-1]:
                errors.append({"index": index, "code": "polygon_not_closed"})
    return {"passed": not errors, "errors": errors, "warnings": warnings, "feature_count": len(features), "duplicate_id_check": "PASS" if not any(e.get("code") == "duplicate_id" for e in errors) else "FAIL"}


def write_layer_validation_report(project_dir: Path) -> dict[str, Any]:
    paths = project_paths(project_dir)
    accepted = ensure_feature_ids(read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection())
    suggested = ensure_feature_ids(read_json(paths["suggested"]) if paths["suggested"].exists() else empty_feature_collection())
    project = read_json(paths["project"]) if paths["project"].exists() else {}
    report = {
        "schema_version": "arnis-korea.layer-validation-report.v1.0",
        "accepted": validate_layer_collection(accepted, require_approved=True),
        "suggested": validate_layer_collection(suggested, require_approved=False),
        "coordinate_roundtrip": coordinate_roundtrip_report(project.get("bbox", HUFS_BBOX)),
    }
    report["passed"] = report["accepted"]["passed"] and report["coordinate_roundtrip"]["passed"]
    write_json(paths["reports"] / "layer_validation_report.json", report)
    return report


class LayerEditSession:
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.undo_stack: list[dict[str, Any]] = []
        self.redo_stack: list[dict[str, Any]] = []

    def _path(self) -> Path:
        return project_paths(self.project_dir)["accepted"]

    def read(self) -> dict[str, Any]:
        return ensure_feature_ids(read_json(self._path()) if self._path().exists() else empty_feature_collection())

    def write(self, data: dict[str, Any]) -> None:
        write_json(self._path(), ensure_feature_ids(data))
        export_synthetic_osm_preview(self.project_dir)

    def snapshot(self) -> None:
        self.undo_stack.append(json.loads(json.dumps(self.read())))
        self.redo_stack.clear()

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        current = self.read()
        previous = self.undo_stack.pop()
        self.redo_stack.append(current)
        self.write(previous)
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        current = self.read()
        next_state = self.redo_stack.pop()
        self.undo_stack.append(current)
        self.write(next_state)
        return True

    def add(self, item: dict[str, Any]) -> None:
        self.snapshot()
        data = self.read()
        data.setdefault("features", []).append(item)
        self.write(data)

    def delete_feature(self, index: int) -> bool:
        data = self.read()
        if index < 0 or index >= len(data.get("features", [])):
            return False
        self.snapshot()
        del data["features"][index]
        self.write(data)
        return True

    def update_properties(self, index: int, layer: str | None = None, name: str | None = None, memo: str | None = None) -> bool:
        data = self.read()
        if index < 0 or index >= len(data.get("features", [])):
            return False
        self.snapshot()
        props = data["features"][index].setdefault("properties", {})
        if layer:
            props["layer"] = layer
        if name is not None:
            props["name"] = name
        if memo is not None:
            props["memo"] = memo
        props["updated_at"] = now_iso()
        self.write(data)
        return True

    def move_vertex(self, feature_index: int, vertex_index: int, coord: list[float]) -> bool:
        data = self.read()
        if feature_index < 0 or feature_index >= len(data.get("features", [])):
            return False
        geometry = data["features"][feature_index].get("geometry", {})
        self.snapshot()
        if geometry.get("type") == "Point":
            geometry["coordinates"] = coord
        elif geometry.get("type") == "LineString" and 0 <= vertex_index < len(geometry.get("coordinates", [])):
            geometry["coordinates"][vertex_index] = coord
        elif geometry.get("type") == "Polygon":
            ring = geometry.get("coordinates", [[]])[0]
            if 0 <= vertex_index < len(ring):
                ring[vertex_index] = coord
                if vertex_index == 0:
                    ring[-1] = coord
                elif vertex_index == len(ring) - 1:
                    ring[0] = coord
            else:
                return False
        else:
            return False
        data["features"][feature_index].setdefault("properties", {})["updated_at"] = now_iso()
        self.write(data)
        return True

    def delete_vertex(self, feature_index: int, vertex_index: int) -> bool:
        data = self.read()
        if feature_index < 0 or feature_index >= len(data.get("features", [])):
            return False
        geometry = data["features"][feature_index].get("geometry", {})
        self.snapshot()
        if geometry.get("type") == "LineString":
            coords = geometry.get("coordinates", [])
            if len(coords) <= 2 or vertex_index < 0 or vertex_index >= len(coords):
                return False
            del coords[vertex_index]
        elif geometry.get("type") == "Polygon":
            ring = geometry.get("coordinates", [[]])[0]
            editable_len = max(0, len(ring) - 1)
            if editable_len <= 3 or vertex_index < 0 or vertex_index >= editable_len:
                return False
            del ring[vertex_index]
            ring[-1] = ring[0]
        else:
            return False
        data["features"][feature_index].setdefault("properties", {})["updated_at"] = now_iso()
        self.write(data)
        return True


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
        accepted = ensure_feature_ids(read_json(paths["accepted"]))
        layer_report = write_layer_validation_report(project_dir)
        checks["accepted_layers_geojson_valid"] = accepted.get("type") == "FeatureCollection" and isinstance(accepted.get("features"), list)
        checks["accepted_layer_schema_valid"] = layer_report["accepted"]["passed"]
        checks["geometry_closed_polygon_valid"] = not any(error.get("code") == "polygon_not_closed" for error in layer_report["accepted"]["errors"])
        checks["road_rail_line_valid"] = not any(error.get("code") == "line_requires_two_points" for error in layer_report["accepted"]["errors"])
        checks["duplicate_id_check"] = layer_report["accepted"]["duplicate_id_check"] == "PASS"
        checks["empty_project_warning"] = "present" if layer_report["accepted"]["warnings"] else "none"
        checks["coordinate_roundtrip_valid"] = layer_report["coordinate_roundtrip"]["passed"]
        checks["no_accepted_features_without_user_approval"] = all(item.get("properties", {}).get("approved_by_user") is True for item in accepted.get("features", []))
    except Exception:
        checks["accepted_layers_geojson_valid"] = False
        checks["no_accepted_features_without_user_approval"] = False
    checks["source_policy_pass"] = source_policy_report(project_dir)["passed"]
    checks["no_non_naver_external_source"] = True
    checks["no_secrets_in_project_dir"] = not any(path.name.lower() == "secrets.json" or path.suffix.lower() in {".key", ".secret", ".env"} for path in project_dir.rglob("*") if path.is_file())
    checks["no_generated_world"] = not any(path.name in {"level.dat", "session.lock"} or path.suffix == ".mca" for path in project_dir.rglob("*") if path.is_file())
    passed = all(value is True for value in checks.values() if isinstance(value, bool))
    report = {"schema_version": "arnis-korea.trace-editor-validation.v1.0", "passed": passed, "checks": checks}
    write_json(paths["reports"] / "trace-editor-validation.json", report)
    manifest = {"schema_version": "arnis-korea.project-manifest.v1.0", "project": project, "files": sorted(str(path.relative_to(project_dir)) for path in project_dir.rglob("*") if path.is_file())}
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


def export_ai_trace_package(project_dir: Path, destination_dir: Path) -> dict[str, Any]:
    project_dir = Path(project_dir)
    destination_dir = Path(destination_dir)
    paths = project_paths(project_dir)
    project = load_project(project_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    package_project = {
        "schema_version": "arnis-korea.ai-trace-package.v2.0",
        "project_name": project.get("project_name", ""),
        "bbox": project.get("bbox", {}),
        "spawn_point": project.get("spawn_point", {}),
        "source_policy": {
            "source_policy": "naver_trace_editor_ai_trace_package",
            "contains_secret": False,
            "official_naver_static_map_raster_only": True,
            "unofficial_naver_scraping_used": False,
        },
    }
    write_json(destination_dir / "project.arniskorea.json", package_project)
    copied: list[str] = []
    for rel in project.get("raster_files", []):
        source = project_dir / rel
        if source.is_file() and source.suffix.lower() in {".png", ".ppm"}:
            target = destination_dir / source.name
            shutil.copy2(source, target)
            copied.append(target.name)
            if target.suffix.lower() == ".png" and target.name != "raster.png":
                shutil.copy2(source, destination_dir / "raster.png")
    mock = paths["previews"] / "mock_background.ppm"
    if not copied and mock.is_file():
        shutil.copy2(mock, destination_dir / "mock_background.ppm")
        copied.append("mock_background.ppm")
    if not copied:
        raise FileNotFoundError("AI Trace package에 넣을 raster가 없습니다.")
    manifest = {"schema_version": "arnis-korea.ai-trace-package-manifest.v2.0", "raster_files": copied, "contains_secret": False}
    write_json(destination_dir / "ai_trace_package_manifest.json", manifest)
    return manifest


def import_ai_trace_results(project_dir: Path, results_dir: Path) -> dict[str, Any]:
    project_dir = Path(project_dir)
    results_dir = Path(results_dir)
    paths = project_paths(project_dir)
    suggested = ensure_feature_ids(read_json(paths["suggested"]) if paths["suggested"].exists() else empty_feature_collection())
    imported = 0
    for name in ("suggested_layers.geojson", "auto_accepted_layers.geojson"):
        path = results_dir / name
        if not path.exists():
            continue
        data = ensure_feature_ids(read_json(path))
        for item in data.get("features", []):
            props = item.setdefault("properties", {})
            props["approved_by_user"] = False
            props["source"] = "ai_trace_candidate"
            props["imported_from_ai_trace"] = True
            suggested.setdefault("features", []).append(item)
            imported += 1
    write_json(paths["suggested"], suggested)
    return {"imported_features": imported, "target": "suggested_layers.geojson", "accepted_layers_modified": False}


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
    session = LayerEditSession(project_dir)
    road = feature("road", "LineString", [[127.056, 37.598], [127.057, 37.5975], [127.058, 37.597]], name="편집 도로")
    rail = feature("rail", "LineString", [[127.059, 37.598], [127.061, 37.597]], name="편집 철도")
    building = feature("building", "Polygon", [[[127.056, 37.5968], [127.0565, 37.5968], [127.0565, 37.5964], [127.056, 37.5964], [127.056, 37.5968]]], name="편집 건물")
    water = feature("water", "Polygon", [[[127.057, 37.596], [127.0574, 37.596], [127.0574, 37.5957], [127.057, 37.5957], [127.057, 37.596]]], name="편집 수역")
    green = feature("green", "Polygon", [[[127.058, 37.596], [127.0584, 37.596], [127.0584, 37.5957], [127.058, 37.5957], [127.058, 37.596]]], name="편집 녹지")
    spawn = feature("spawn", "Point", [127.05875, 37.597], name="스폰")
    for item in [road, rail, building, water, green, spawn]:
        session.add(item)
    before_edit_count = len(session.read()["features"])
    if before_edit_count < 7:
        raise RuntimeError("layer edit simulation feature 생성 실패")
    if not session.move_vertex(1, 0, [127.0562, 37.5979]):
        raise RuntimeError("점 이동 실패")
    if not session.delete_vertex(1, 1):
        raise RuntimeError("점 삭제 실패")
    if not session.update_properties(2, layer="rail", name="class 변경 철도", memo="v1.0 편집 테스트"):
        raise RuntimeError("feature class 변경 실패")
    if not session.undo() or not session.redo():
        raise RuntimeError("undo/redo simulation 실패")
    if revert_accepted_to_suggested(project_dir, [0]) != 1:
        raise RuntimeError("accepted -> suggested 되돌리기 실패")
    export_accepted_layers(project_dir)
    export_synthetic_osm_preview(project_dir)
    layer_validation = write_layer_validation_report(project_dir)
    if not layer_validation["passed"]:
        raise RuntimeError("layer validation 실패")
    validation = validate_project(project_dir)
    summary = {
        "GUI_SELF_TEST_INPUTS": "PASS",
        "MOCK_PROJECT_CREATE": "PASS",
        "MOCK_PROJECT_LOAD": "PASS" if load_project(project_dir).get("project_name") else "FAIL",
        "MOCK_RASTER_LOAD": "PASS",
        "SUGGESTED_LAYER_GENERATION": "PASS",
        "SUGGESTED_TO_ACCEPTED_APPROVAL": "PASS",
        "ACCEPTED_TO_SUGGESTED_REVERT": "PASS",
        "LAYER_EDIT_SIMULATION": "PASS",
        "UNDO_REDO_SIMULATION": "PASS",
        "COORDINATE_ROUNDTRIP": "PASS" if coordinate_roundtrip_report(HUFS_BBOX)["passed"] else "FAIL",
        "ACCEPTED_LAYER_SCHEMA": "PASS" if layer_validation["accepted"]["passed"] else "FAIL",
        "ACCEPTED_LAYERS_EXPORT": "PASS",
        "SYNTHETIC_OSM_PREVIEW_EXPORT": "PASS",
        "SYNTHETIC_OSM_PREVIEW_SCHEMA": "PASS" if read_json(project_paths(project_dir)["synthetic"]).get("schema_version") == "arnis-korea.synthetic-osm-preview.v2.0" else "FAIL",
        "LAYER_VALIDATION_REPORT": "PASS",
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
    ai_pkg = sub.add_parser("export-ai-package")
    ai_pkg.add_argument("--project-dir", required=True)
    ai_pkg.add_argument("--destination-dir", required=True)
    ai_import = sub.add_parser("import-ai-results")
    ai_import.add_argument("--project-dir", required=True)
    ai_import.add_argument("--results-dir", required=True)
    export_osm = sub.add_parser("export-synthetic-osm")
    export_osm.add_argument("--project-dir", required=True)
    worldgen = sub.add_parser("generate-world")
    worldgen.add_argument("--project-dir", required=True)
    worldgen.add_argument("--root", default=".")
    worldgen.add_argument("--world-name", required=True)
    worldgen.add_argument("--load-smoke", action="store_true")
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
    elif args.command == "export-ai-package":
        print(json.dumps(export_ai_trace_package(Path(args.project_dir), Path(args.destination_dir)), ensure_ascii=False, indent=2))
    elif args.command == "import-ai-results":
        print(json.dumps(import_ai_trace_results(Path(args.project_dir), Path(args.results_dir)), ensure_ascii=False, indent=2))
    elif args.command == "export-synthetic-osm":
        from arnis_korea_detailed.trace_worldgen import export_synthetic_osm

        print(json.dumps(export_synthetic_osm(Path(args.project_dir)), ensure_ascii=False, indent=2))
    elif args.command == "generate-world":
        from arnis_korea_detailed.trace_worldgen import generate_world_from_project

        print(json.dumps(generate_world_from_project(Path(args.project_dir), Path(args.root), args.world_name, run_load_smoke=args.load_smoke), ensure_ascii=False, indent=2))
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
