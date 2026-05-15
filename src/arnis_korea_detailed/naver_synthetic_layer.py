from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .korea_feature_schema import KoreaFeature


CLASS_TO_TAGS = {
    "road_major": {"highway": "primary"},
    "road_minor": {"highway": "residential"},
    "road": {"highway": "residential"},
    "building_candidate": {"building": "yes"},
    "building": {"building": "yes"},
    "green": {"landuse": "grass"},
    "water": {"natural": "water"},
    "rail": {"railway": "rail"},
    "campus_area": {"amenity": "university"},
}

WORLD_HINTS = {
    "road_major": {"block": "light_gray_concrete", "edge_block": "gray_concrete", "width": 5},
    "road_minor": {"block": "gray_concrete", "width": 3},
    "road": {"block": "gray_concrete", "width": 3},
    "building_candidate": {"block": "light_gray_concrete", "outline_block": "smooth_stone", "height": 3},
    "building": {"block": "white_concrete", "outline_block": "smooth_stone", "height": 3},
    "green": {"block": "grass_block"},
    "water": {"block": "water"},
    "rail": {"block": "iron_block", "width": 1},
    "campus_area": {"block": "smooth_stone", "outline_block": "light_gray_concrete", "height": 3},
}


def _feature_class(feature: KoreaFeature) -> str:
    if feature.feature_class == "building":
        return "building_candidate"
    if feature.feature_class == "road":
        area = int(feature.properties.get("pixel_area", 0))
        return "road_major" if area >= 100 else "road_minor"
    return feature.feature_class


def build_synthetic_documents(
    features: list[KoreaFeature],
    bbox: dict[str, float],
    source_mode: str,
    building_mode: str,
    road_width_multiplier: float = 1.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    osm_elements: list[dict[str, Any]] = []
    world_features: list[dict[str, Any]] = []
    node_id = 9_000_000_000
    way_id = 9_100_000_000
    for index, feature in enumerate(features, start=1):
        cls = _feature_class(feature)
        if cls in {"building", "building_candidate", "campus_area"} and building_mode == "roads-green-water-only":
            continue
        tags = dict(CLASS_TO_TAGS.get(cls, {}))
        hint = dict(WORLD_HINTS.get(cls, {}))
        if cls in {"road", "road_major", "road_minor"}:
            hint["width"] = max(1, int(round(float(hint.get("width", 2)) * road_width_multiplier)))
        if cls in {"building", "building_candidate", "campus_area"}:
            hint["building_mode"] = building_mode
            hint["height_source"] = "heuristic_from_naver_raster"
            if building_mode == "footprint-only":
                hint["height"] = 1
            elif building_mode == "map-readable":
                hint["height"] = 2 if int(feature.properties.get("pixel_area", 0)) < 300 else 3
            elif building_mode == "low-rise":
                hint["height"] = min(5, max(2, int(feature.properties.get("pixel_area", 0)) // 180 + 2))
            elif building_mode == "full-experimental":
                hint["height"] = 10
                hint["block"] = "stone_bricks"
            if "building" in tags:
                tags["building:levels"] = str(max(1, int(hint.get("height", 8)) // 3))
        coords = _clip_coordinates(feature.coordinates, bbox)
        if len(coords) < 2:
            continue
        if feature.geometry_type == "polygon":
            if len(coords) < 3:
                continue
            if coords[0] != coords[-1]:
                coords.append(coords[0])
        current_nodes: list[int] = []
        for lon, lat in coords:
            node_id += 1
            current_nodes.append(node_id)
            osm_elements.append({"type": "node", "id": node_id, "lat": lat, "lon": lon})
        way_id += 1
        osm_elements.append({"type": "way", "id": way_id, "nodes": current_nodes, "tags": tags})
        common = {
            "id": f"naver-synth-{index:05d}",
            "source": "naver_static_raster",
            "class": cls,
            "confidence": float(feature.properties.get("confidence", 0.6)),
            "geometry_type": feature.geometry_type,
            "coordinates": coords,
            "bbox": feature.properties.get("bbox"),
            "pixel_area": feature.properties.get("pixel_area"),
        }
        world_features.append({**common, "world_hint": hint, "style_hint": feature.properties.get("style_profile", "generic")})
    metadata = {
        "source_mode": source_mode,
        "bbox": bbox,
        "feature_count": len(features),
        "render_feature_count": len(world_features),
        "derived_from": "official_naver_static_raster_or_mock_fixture",
        "redistribution": "private_local_output_only",
        "building_mode": building_mode,
        "road_width_multiplier": road_width_multiplier,
    }
    return (
        {"version": 0.6, "generator": "arnis-korea-naver-only", "elements": osm_elements},
        {"schema": "arnis-korea.naver_world_features.v1", "metadata": metadata, "features": world_features},
    )


def _clip_coordinates(coordinates: list[list[float]], bbox: dict[str, float]) -> list[list[float]]:
    clipped: list[list[float]] = []
    for point in coordinates:
        if len(point) < 2:
            continue
        lon = min(max(float(point[0]), bbox["min_lng"]), bbox["max_lng"])
        lat = min(max(float(point[1]), bbox["min_lat"]), bbox["max_lat"])
        rounded = [round(lon, 8), round(lat, 8)]
        if rounded != clipped[-1:] and (not clipped or rounded != clipped[-1]):
            clipped.append(rounded)
    return clipped


def write_synthetic_layer(
    output_dir: Path,
    features: list[KoreaFeature],
    bbox: dict[str, float],
    source_mode: str,
    building_mode: str,
    road_width_multiplier: float = 1.0,
) -> dict[str, str]:
    osm_doc, world_doc = build_synthetic_documents(features, bbox, source_mode, building_mode, road_width_multiplier)
    osm_path = output_dir / "naver_synthetic_osm.json"
    world_path = output_dir / "naver_world_features.json"
    osm_path.write_text(json.dumps(osm_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    world_path.write_text(json.dumps(world_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"synthetic_osm": str(osm_path), "world_features": str(world_path)}
