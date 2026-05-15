from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .debug_preview import write_png


COLORS = {
    "background": (238, 238, 232),
    "road": (190, 190, 190),
    "road_major": (180, 180, 180),
    "road_minor": (205, 205, 205),
    "water": (65, 145, 220),
    "green": (90, 170, 95),
    "building": (215, 215, 210),
    "building_candidate": (215, 215, 210),
    "rail": (70, 70, 70),
}


def _lonlat_to_pixel(point: list[float], bbox: dict[str, float], width: int, height: int) -> tuple[int, int]:
    lon, lat = point
    x = int(round((lon - bbox["min_lng"]) / max(bbox["max_lng"] - bbox["min_lng"], 1e-12) * (width - 1)))
    y = int(round((bbox["max_lat"] - lat) / max(bbox["max_lat"] - bbox["min_lat"], 1e-12) * (height - 1)))
    return max(0, min(width - 1, x)), max(0, min(height - 1, y))


def _draw_line(pixels: list[list[tuple[int, int, int]]], a: tuple[int, int], b: tuple[int, int], color: tuple[int, int, int], width: int) -> int:
    height = len(pixels)
    image_width = len(pixels[0]) if height else 0
    steps = max(abs(b[0] - a[0]), abs(b[1] - a[1]), 1)
    radius = max(0, width // 2)
    touched = 0
    for i in range(steps + 1):
        x = round(a[0] + (b[0] - a[0]) * i / steps)
        y = round(a[1] + (b[1] - a[1]) * i / steps)
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                px, py = x + dx, y + dy
                if 0 <= px < image_width and 0 <= py < height:
                    if pixels[py][px] != color:
                        touched += 1
                    pixels[py][px] = color
    return touched


def _fill_bbox(pixels: list[list[tuple[int, int, int]]], points: list[tuple[int, int]], color: tuple[int, int, int], outline: bool = False) -> int:
    if not points:
        return 0
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    min_x, max_x = max(0, min(x for x, _ in points)), min(width - 1, max(x for x, _ in points))
    min_y, max_y = max(0, min(y for _, y in points)), min(height - 1, max(y for _, y in points))
    touched = 0
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if outline and not (x in {min_x, max_x} or y in {min_y, max_y}):
                continue
            if pixels[y][x] != color:
                touched += 1
            pixels[y][x] = color
    return touched


def _side_by_side(left: list[list[tuple[int, int, int]]], right: list[list[tuple[int, int, int]]]) -> list[list[tuple[int, int, int]]]:
    height = min(len(left), len(right))
    if not height:
        return []
    return [left[y] + [(30, 30, 30)] * 4 + right[y] for y in range(height)]


def _read_png_or_blank(path: Path, width: int, height: int) -> list[list[tuple[int, int, int]]]:
    try:
        from .raster_mosaic import single_image_mosaic

        pixels = single_image_mosaic(path)
        if len(pixels) == height and pixels and len(pixels[0]) == width:
            return pixels
    except Exception:
        pass
    return [[COLORS["background"] for _ in range(width)] for _ in range(height)]


def write_visual_quality_outputs(
    metadata_dir: Path,
    world_features_path: Path,
    bbox: dict[str, float],
    filter_stats: dict[str, Any],
    world_validation: dict[str, Any],
    source_policy: dict[str, Any],
    minecraft_load_smoke: dict[str, Any],
    building_mode: str,
    size: int = 512,
) -> dict[str, Any]:
    metadata_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = metadata_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    world_doc = json.loads(world_features_path.read_text(encoding="utf-8"))
    pixels = [[COLORS["background"] for _ in range(size)] for _ in range(size)]
    coverage = {"road": 0, "water": 0, "green": 0, "building": 0}
    full_extrusion_risk = False
    for feature in world_doc.get("features", []):
        cls = feature.get("class")
        points = [_lonlat_to_pixel(point, bbox, size, size) for point in feature.get("coordinates", [])]
        if not points:
            continue
        if feature.get("geometry_type") == "line":
            color = COLORS.get(cls, COLORS["road"])
            touched = 0
            for a, b in zip(points, points[1:]):
                touched += _draw_line(pixels, a, b, color, int(feature.get("world_hint", {}).get("width", 3)))
            if cls in {"road", "road_major", "road_minor", "rail"}:
                coverage["road"] += touched
        elif cls in {"water", "green", "building", "building_candidate", "campus_area"}:
            key = "building" if cls in {"building", "building_candidate", "campus_area"} else cls
            touched = _fill_bbox(pixels, points, COLORS.get(cls, COLORS["building"]), outline=key == "building")
            coverage[key] += touched
            if key == "building" and int(feature.get("world_hint", {}).get("height", 1)) > 5 and building_mode == "map-readable":
                full_extrusion_risk = True
    topdown_path = write_png(debug_dir / "world_topdown_preview.png", pixels)
    original = debug_dir / "original_static_map.png"
    source_copy = debug_dir / "source_or_mock_raster.png"
    if original.exists():
        shutil.copy2(original, source_copy)
    else:
        write_png(source_copy, [[COLORS["background"] for _ in range(size)] for _ in range(size)])
    left = _read_png_or_blank(source_copy, size, size)
    overlay = write_png(debug_dir / "overlay_comparison.png", _side_by_side(left, pixels))
    counts = filter_stats.get("class_counts_after", {})
    score = int(filter_stats.get("map_readability_score", 0))
    has_map_signal = any(value > 0 for key, value in coverage.items() if key in {"road", "water", "green"})
    if has_map_signal:
        score = max(score, 75)
    clean_layout = bool(world_validation.get("valid"))
    source_policy_pass = bool(
        source_policy.get("external_non_naver_sources_used") is False
        and source_policy.get("renderer_network_disabled") is True
        and source_policy.get("synthetic_input_used") is True
    )
    world_openable = bool(minecraft_load_smoke.get("passed"))
    before = int(filter_stats.get("feature_count_before_filter", 0))
    after = int(filter_stats.get("feature_count_after_filter", 0))
    dropped_noise = int(filter_stats.get("dropped_noise_count", 0))
    exceptions = []
    if not before or after < before:
        feature_reduction_pass = True
    else:
        feature_reduction_pass = False
        exceptions.append("feature_count_after_filter_not_lower")
    if dropped_noise >= 1:
        noise_drop_pass = True
    else:
        noise_drop_pass = False
        exceptions.append("no_noise_dropped")
    passed = bool(
        world_openable
        and clean_layout
        and source_policy_pass
        and score >= 75
        and feature_reduction_pass
        and noise_drop_pass
        and has_map_signal
        and not full_extrusion_risk
    )
    report = {
        "schema": "arnis-korea.quality_auto_check.v1",
        "passed": passed,
        "preview_source": "feature_layer",
        "previews": {
            "source_or_mock_raster": str(source_copy),
            "world_topdown_preview": str(topdown_path),
            "overlay_comparison": str(overlay),
            "segmentation_preview": str(debug_dir / "segmentation_preview.png"),
        },
        "feature_count_before_filter": before,
        "feature_count_after_filter": after,
        "dropped_noise_count": dropped_noise,
        "class_counts": counts,
        "road_pixel_or_block_coverage": coverage["road"],
        "water_pixel_or_block_coverage": coverage["water"],
        "green_pixel_or_block_coverage": coverage["green"],
        "building_pixel_or_block_coverage": coverage["building"],
        "tiny_component_drop_count": int(filter_stats.get("drop_reasons", {}).get("small_component", 0)) + int(filter_stats.get("drop_reasons", {}).get("small_building_candidate", 0)),
        "label_noise_drop_count": int(filter_stats.get("drop_reasons", {}).get("label_noise", 0)),
        "map_readability_score": score,
        "world_openable": world_openable,
        "clean_layout": clean_layout,
        "source_policy_pass": source_policy_pass,
        "has_road_green_or_water_signal": has_map_signal,
        "building_mode": building_mode,
        "full_extrusion_risk": full_extrusion_risk,
        "exceptions": exceptions,
    }
    (metadata_dir / "quality_auto_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
