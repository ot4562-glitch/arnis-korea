from __future__ import annotations

from collections import Counter
from typing import Any

from .korea_feature_schema import KoreaFeature


NOISE_FILTER_PRESETS = {
    "low": {"min_area": 3, "building_min_area": 48, "road_min_length": 8, "max_aspect_polygon": 18.0, "class_caps": {"building": 180, "building_candidate": 180}},
    "medium": {"min_area": 6, "building_min_area": 96, "road_min_length": 12, "max_aspect_polygon": 14.0, "class_caps": {"building": 120, "building_candidate": 120}},
    "high": {"min_area": 10, "building_min_area": 160, "road_min_length": 16, "max_aspect_polygon": 10.0, "class_caps": {"building": 80, "building_candidate": 80, "road": 160, "road_major": 80, "road_minor": 120}},
}


def _blank_stats(features: list[KoreaFeature], preset: str) -> dict[str, Any]:
    counts = Counter(feature.feature_class for feature in features)
    return {
        "noise_filter_level": preset,
        "feature_count_before_filter": len(features),
        "feature_count_after_filter": len(features),
        "class_counts_before": dict(sorted(counts.items())),
        "class_counts_after": dict(sorted(counts.items())),
        "filtered_count": 0,
        "dropped_noise_count": 0,
        "drop_reasons": {},
    }


def cleanup_feature_set(
    features: list[KoreaFeature],
    min_pixel_area: int | None = None,
    building_min_area: int | None = None,
    min_line_length: int | None = None,
    noise_filter_level: str = "medium",
    simplify_decimals: int = 8,
) -> tuple[list[KoreaFeature], dict[str, Any]]:
    preset_name = noise_filter_level if noise_filter_level in NOISE_FILTER_PRESETS else "medium"
    preset = NOISE_FILTER_PRESETS[preset_name]
    min_area = min_pixel_area if min_pixel_area is not None else int(preset["min_area"])
    min_building = building_min_area if building_min_area is not None else int(preset["building_min_area"])
    min_length = min_line_length if min_line_length is not None else int(preset["road_min_length"])
    max_aspect_polygon = float(preset["max_aspect_polygon"])
    class_caps = dict(preset.get("class_caps", {}))
    kept_by_class: Counter[str] = Counter()
    before_counts = Counter(feature.feature_class for feature in features)
    drop_reasons: Counter[str] = Counter()
    cleaned: list[KoreaFeature] = []

    for feature in features:
        cls = feature.feature_class
        pixel_area = int(feature.properties.get("pixel_area", min_area))
        pixel_width = int(feature.properties.get("pixel_width", 1))
        pixel_height = int(feature.properties.get("pixel_height", 1))
        aspect = float(feature.properties.get("aspect_ratio", 1.0))
        line_length = int(feature.properties.get("length_estimate_px", max(pixel_width, pixel_height)))
        reason: str | None = None
        if cls == "label_noise":
            reason = "label_noise"
        elif pixel_area < min_area:
            reason = "small_component"
        elif cls in {"building", "building_candidate"} and pixel_area < min_building:
            reason = "small_building_candidate"
        elif feature.geometry_type == "polygon" and (min(pixel_width, pixel_height) <= 2 or aspect > max_aspect_polygon):
            reason = "thin_polygon_noise"
        elif feature.geometry_type == "line" and line_length < min_length:
            reason = "short_line"
        elif kept_by_class[cls] >= int(class_caps.get(cls, 10**9)):
            reason = "class_cap"

        if reason:
            drop_reasons[reason] += 1
            continue

        coords = []
        previous: list[float] | None = None
        for lon, lat in feature.coordinates:
            point = [round(lon, simplify_decimals), round(lat, simplify_decimals)]
            if point != previous:
                coords.append(point)
            previous = point
        if feature.geometry_type == "polygon" and coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        kept_by_class[cls] += 1
        cleaned.append(
            KoreaFeature(
                id=feature.id,
                feature_class=feature.feature_class,
                geometry_type=feature.geometry_type,
                coordinates=coords,
                properties={
                    **feature.properties,
                    "geometry_cleanup": "noise_filtered_points_simplified",
                    "noise_filter_level": preset_name,
                },
            )
        )

    after_counts = Counter(feature.feature_class for feature in cleaned)
    stats = {
        "noise_filter_level": preset_name,
        "feature_count_before_filter": len(features),
        "feature_count_after_filter": len(cleaned),
        "class_counts_before": dict(sorted(before_counts.items())),
        "class_counts_after": dict(sorted(after_counts.items())),
        "filtered_count": len(features) - len(cleaned),
        "dropped_noise_count": int(sum(drop_reasons.values())),
        "drop_reasons": dict(sorted(drop_reasons.items())),
        "building_count_before": before_counts.get("building", 0) + before_counts.get("building_candidate", 0),
        "building_count_after": after_counts.get("building", 0) + after_counts.get("building_candidate", 0),
        "road_feature_count_after": after_counts.get("road", 0) + after_counts.get("road_major", 0) + after_counts.get("road_minor", 0),
        "water_green_feature_count_after": after_counts.get("water", 0) + after_counts.get("green", 0),
    }
    return cleaned, stats


def cleanup_features(
    features: list[KoreaFeature],
    min_pixel_area: int = 4,
    simplify_decimals: int = 8,
) -> list[KoreaFeature]:
    cleaned, _stats = cleanup_feature_set(features, min_pixel_area=min_pixel_area, noise_filter_level="low", simplify_decimals=simplify_decimals)
    return cleaned
