from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SUPPORTED_CLASSES = {
    "road",
    "road_major",
    "road_minor",
    "building",
    "building_candidate",
    "water",
    "green",
    "rail",
    "campus_area",
    "background",
    "label_noise",
}
SUPPORTED_STYLE_PROFILES = {
    "apartment",
    "villa",
    "shop",
    "school",
    "office",
    "campus",
    "landmark",
    "generic",
}

STYLE_PROFILES = {
    "apartment": {"height_fallback_levels": 18, "palette": "korean_apartment"},
    "villa": {"height_fallback_levels": 4, "palette": "lowrise_villa"},
    "shop": {"height_fallback_levels": 3, "palette": "shop_street"},
    "school": {"height_fallback_levels": 5, "palette": "campus_school"},
    "office": {"height_fallback_levels": 12, "palette": "office_core"},
    "campus": {"height_fallback_levels": 6, "palette": "korean_campus"},
    "landmark": {"height_fallback_levels": 10, "palette": "landmark"},
    "generic": {"height_fallback_levels": 5, "palette": "generic_korea"},
}

HEIGHT_SOURCE_PRIORITY = [
    "osm_building_levels",
    "osm_height",
    "public_building_data_future_adapter",
    "dem_dsm_future_adapter",
    "heuristic_fallback",
]

MINECRAFT_PALETTE_NOTES = {
    "korean_apartment": ["white_concrete", "light_gray_concrete", "glass_pane", "stone_bricks"],
    "korean_campus": ["bricks", "smooth_stone", "glass", "oak_leaves"],
    "shop_street": ["quartz_block", "terracotta", "glass_pane", "lantern"],
    "road_sidewalk": ["black_concrete", "gray_concrete", "stone_slab", "white_concrete"],
    "rail_water_green": ["iron_block", "gravel", "water", "grass_block", "oak_leaves"],
}


@dataclass
class KoreaFeature:
    id: str
    feature_class: str
    geometry_type: str
    coordinates: list[list[float]]
    properties: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.feature_class not in SUPPORTED_CLASSES:
            raise ValueError(f"unsupported feature_class={self.feature_class}")
        if self.geometry_type not in {"polygon", "line"}:
            raise ValueError(f"unsupported geometry_type={self.geometry_type}")
        if not self.coordinates:
            raise ValueError("coordinates must not be empty")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


def normalized_document(
    bbox: dict[str, float],
    source_mode: str,
    features: list[KoreaFeature],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "arnis-korea-detailed.normalized_features.v1",
        "source_mode": source_mode,
        "bbox": bbox,
        "feature_count": len(features),
        "features": [feature.to_dict() for feature in features],
        "terrain": {
            "elevation_source": "placeholder",
            "dem_required_for_real_generation": True,
        },
        "metadata": metadata or {},
    }
