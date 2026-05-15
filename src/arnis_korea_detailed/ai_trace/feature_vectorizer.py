from __future__ import annotations

from typing import Any

from arnis_korea_detailed.ai_trace.confidence_gate import confidence_for
from arnis_korea_detailed.trace_editor_core import SUGGESTED_SOURCE, feature, pixel_to_lng_lat


def vectorize_segments(width: int, height: int, bbox: dict[str, float], segments: dict[str, list[tuple[int, int]]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for kind, points in segments.items():
        if len(points) < 4:
            continue
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        confidence = confidence_for(kind, points, width, height)
        if kind == "road":
            y_mid = (min_y + max_y) / 2
            coords = [pixel_to_lng_lat(min_x, y_mid, width, height, bbox), pixel_to_lng_lat(max_x, y_mid, width, height, bbox)]
            item = feature("road", "LineString", coords, name="AI 후보 도로", source=SUGGESTED_SOURCE, approved=False, confidence=confidence)
        else:
            ring = [
                pixel_to_lng_lat(min_x, min_y, width, height, bbox),
                pixel_to_lng_lat(max_x, min_y, width, height, bbox),
                pixel_to_lng_lat(max_x, max_y, width, height, bbox),
                pixel_to_lng_lat(min_x, max_y, width, height, bbox),
                pixel_to_lng_lat(min_x, min_y, width, height, bbox),
            ]
            item = feature(kind, "Polygon", [ring], name=f"AI 후보 {kind}", source=SUGGESTED_SOURCE, approved=False, confidence=confidence)
        item["properties"]["ai_trace"] = True
        item["properties"]["ai_trace_status"] = "candidate"
        output.append(item)
    return output
