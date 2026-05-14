from __future__ import annotations

from .korea_feature_schema import KoreaFeature


def cleanup_features(
    features: list[KoreaFeature],
    min_pixel_area: int = 4,
    simplify_decimals: int = 8,
) -> list[KoreaFeature]:
    cleaned: list[KoreaFeature] = []
    for feature in features:
        pixel_area = int(feature.properties.get("pixel_area", min_pixel_area))
        if pixel_area < min_pixel_area:
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
        cleaned.append(
            KoreaFeature(
                id=feature.id,
                feature_class=feature.feature_class,
                geometry_type=feature.geometry_type,
                coordinates=coords,
                properties={**feature.properties, "geometry_cleanup": "small_objects_removed_and_points_simplified"},
            )
        )
    return cleaned
