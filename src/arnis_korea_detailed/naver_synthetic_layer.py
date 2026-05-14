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
    "road_major": {"block": "black_concrete", "width": 5},
    "road_minor": {"block": "gray_concrete", "width": 3},
    "road": {"block": "gray_concrete", "width": 3},
    "building_candidate": {"block": "light_gray_concrete", "height": 10},
    "building": {"block": "stone_bricks", "height": 10},
    "green": {"block": "grass_block"},
    "water": {"block": "water"},
    "rail": {"block": "iron_block", "width": 1},
    "campus_area": {"block": "smooth_stone", "height": 8},
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
) -> tuple[dict[str, Any], dict[str, Any]]:
    osm_features: list[dict[str, Any]] = []
    world_features: list[dict[str, Any]] = []
    for index, feature in enumerate(features, start=1):
        cls = _feature_class(feature)
        tags = CLASS_TO_TAGS.get(cls, {})
        hint = dict(WORLD_HINTS.get(cls, {}))
        if cls in {"building", "building_candidate", "campus_area"}:
            hint["building_mode"] = building_mode
            hint["height_source"] = "heuristic_from_naver_raster"
            if building_mode == "footprint-only":
                hint["height"] = 2
            elif building_mode == "campus-style":
                hint["height"] = 8
                hint["block"] = "bricks"
        common = {
            "id": f"naver-synth-{index:05d}",
            "source": "naver_static_raster",
            "class": cls,
            "confidence": float(feature.properties.get("confidence", 0.6)),
            "geometry_type": feature.geometry_type,
            "coordinates": feature.coordinates,
            "bbox": feature.properties.get("bbox"),
            "pixel_area": feature.properties.get("pixel_area"),
        }
        osm_features.append({**common, "tags": tags})
        world_features.append({**common, "world_hint": hint, "style_hint": feature.properties.get("style_profile", "generic")})
    metadata = {
        "source_mode": source_mode,
        "bbox": bbox,
        "feature_count": len(features),
        "derived_from": "official_naver_static_raster_or_mock_fixture",
        "redistribution": "private_local_output_only",
    }
    return (
        {"schema": "arnis-korea.naver_synthetic_osm.v1", "metadata": metadata, "elements": osm_features},
        {"schema": "arnis-korea.naver_world_features.v1", "metadata": metadata, "features": world_features},
    )


def write_synthetic_layer(
    output_dir: Path,
    features: list[KoreaFeature],
    bbox: dict[str, float],
    source_mode: str,
    building_mode: str,
) -> dict[str, str]:
    osm_doc, world_doc = build_synthetic_documents(features, bbox, source_mode, building_mode)
    osm_path = output_dir / "naver_synthetic_osm.json"
    world_path = output_dir / "naver_world_features.json"
    osm_path.write_text(json.dumps(osm_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    world_path.write_text(json.dumps(world_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"synthetic_osm": str(osm_path), "world_features": str(world_path)}
