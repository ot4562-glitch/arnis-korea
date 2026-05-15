from __future__ import annotations

from collections import deque

from .korea_feature_schema import KoreaFeature


def _pixel_to_lonlat(x: int, y: int, width: int, height: int, bbox: dict[str, float]) -> list[float]:
    lon = bbox["min_lng"] + (bbox["max_lng"] - bbox["min_lng"]) * (x / max(width - 1, 1))
    lat = bbox["max_lat"] - (bbox["max_lat"] - bbox["min_lat"]) * (y / max(height - 1, 1))
    return [round(lon, 8), round(lat, 8)]


def _bbox_polygon(xs: list[int], ys: list[int], width: int, height: int, bbox: dict[str, float]) -> list[list[float]]:
    min_x, max_x = min(xs), max(xs) + 1
    min_y, max_y = min(ys), max(ys) + 1
    return [
        _pixel_to_lonlat(min_x, min_y, width, height, bbox),
        _pixel_to_lonlat(max_x, min_y, width, height, bbox),
        _pixel_to_lonlat(max_x, max_y, width, height, bbox),
        _pixel_to_lonlat(min_x, max_y, width, height, bbox),
        _pixel_to_lonlat(min_x, min_y, width, height, bbox),
    ]


def _line_from_bbox(xs: list[int], ys: list[int], width: int, height: int, bbox: dict[str, float]) -> list[list[float]]:
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if (max_x - min_x) >= (max_y - min_y):
        mid_y = (min_y + max_y) // 2
        return [
            _pixel_to_lonlat(min_x, mid_y, width, height, bbox),
            _pixel_to_lonlat(max_x, mid_y, width, height, bbox),
        ]
    mid_x = (min_x + max_x) // 2
    return [
        _pixel_to_lonlat(mid_x, min_y, width, height, bbox),
        _pixel_to_lonlat(mid_x, max_y, width, height, bbox),
    ]


def vectorize_segments(segments: list[list[str]], bbox: dict[str, float]) -> list[KoreaFeature]:
    height = len(segments)
    width = len(segments[0]) if height else 0
    visited = [[False for _ in range(width)] for _ in range(height)]
    features: list[KoreaFeature] = []
    feature_index = 1

    for y in range(height):
        for x in range(width):
            feature_class = segments[y][x]
            if visited[y][x] or feature_class == "background":
                continue
            queue = deque([(x, y)])
            visited[y][x] = True
            xs: list[int] = []
            ys: list[int] = []
            while queue:
                cx, cy = queue.popleft()
                xs.append(cx)
                ys.append(cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx]:
                        if segments[ny][nx] == feature_class:
                            visited[ny][nx] = True
                            queue.append((nx, ny))
            if len(xs) < 4 and feature_class != "label_noise":
                continue

            geometry_type = "line" if feature_class in {"road", "road_major", "road_minor", "rail"} else "polygon"
            coords = (
                _line_from_bbox(xs, ys, width, height, bbox)
                if geometry_type == "line"
                else _bbox_polygon(xs, ys, width, height, bbox)
            )
            properties = {
                "pixel_area": len(xs),
                "pixel_width": max(xs) - min(xs) + 1,
                "pixel_height": max(ys) - min(ys) + 1,
                "aspect_ratio": round((max(max(xs) - min(xs) + 1, max(ys) - min(ys) + 1) / max(1, min(max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))), 3),
                "length_estimate_px": max(max(xs) - min(xs) + 1, max(ys) - min(ys) + 1) if geometry_type == "line" else None,
                "bbox": [
                    _pixel_to_lonlat(min(xs), max(ys), width, height, bbox),
                    _pixel_to_lonlat(max(xs), min(ys), width, height, bbox),
                ],
                "confidence": 0.72 if feature_class != "background" else 0.2,
                "height_source": "heuristic_fallback" if feature_class == "building" else None,
                "estimated_levels": 5 if feature_class == "building" else None,
                "building_type": "generic" if feature_class == "building" else None,
                "style_profile": "generic",
            }
            features.append(
                KoreaFeature(
                    id=f"mock-{feature_index:04d}",
                    feature_class=feature_class,
                    geometry_type=geometry_type,
                    coordinates=coords,
                    properties={k: v for k, v in properties.items() if v is not None},
                )
            )
            feature_index += 1

    return features
