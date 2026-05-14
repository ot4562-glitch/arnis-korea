from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

EARTH_CIRCUMFERENCE_M = 40075016.686


@dataclass
class StaticMapTilePlan:
    row: int
    col: int
    center: list[float]
    bbox: dict[str, float]
    params: dict[str, Any]


def meters_per_pixel(level: int, latitude: float, scale: int = 1) -> float:
    zoom = max(0, min(20, level))
    latitude_factor = math.cos(math.radians(latitude))
    return (EARTH_CIRCUMFERENCE_M * latitude_factor) / (256 * (2**zoom) * scale)


def estimate_bbox_size_m(bbox: dict[str, float]) -> tuple[float, float]:
    mid_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2
    lat_m = (bbox["max_lat"] - bbox["min_lat"]) * 111_320
    lon_m = (bbox["max_lng"] - bbox["min_lng"]) * 111_320 * math.cos(math.radians(mid_lat))
    return abs(lon_m), abs(lat_m)


def split_static_map_requests(
    bbox: dict[str, float],
    level: int = 16,
    width: int = 1024,
    height: int = 1024,
    scale: int = 2,
    maptype: str = "basic",
    fmt: str = "png",
    crs: str = "EPSG:4326",
    lang: str = "ko",
    dataversion: str | None = None,
) -> dict[str, Any]:
    if not (1 <= width <= 1024 and 1 <= height <= 1024):
        raise ValueError("Static Map w/h must be 1..1024")
    if scale not in {1, 2}:
        raise ValueError("Static Map scale must be 1 or 2")
    if not (0 <= level <= 20):
        raise ValueError("Static Map level must be 0..20")
    if maptype not in {"basic", "traffic", "satellite", "satellite_base", "terrain"}:
        raise ValueError("unsupported maptype")
    if fmt not in {"jpg", "jpeg", "png8", "png"}:
        raise ValueError("unsupported format")

    mid_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2
    mpp = meters_per_pixel(level, mid_lat, scale=scale)
    bbox_w_m, bbox_h_m = estimate_bbox_size_m(bbox)
    tile_w_m = width * mpp
    tile_h_m = height * mpp
    cols = max(1, math.ceil(bbox_w_m / tile_w_m))
    rows = max(1, math.ceil(bbox_h_m / tile_h_m))

    tiles: list[StaticMapTilePlan] = []
    lat_step = (bbox["max_lat"] - bbox["min_lat"]) / rows
    lng_step = (bbox["max_lng"] - bbox["min_lng"]) / cols
    for row in range(rows):
        for col in range(cols):
            min_lat = bbox["min_lat"] + row * lat_step
            max_lat = bbox["min_lat"] + (row + 1) * lat_step
            min_lng = bbox["min_lng"] + col * lng_step
            max_lng = bbox["min_lng"] + (col + 1) * lng_step
            center_lat = (min_lat + max_lat) / 2
            center_lng = (min_lng + max_lng) / 2
            params: dict[str, Any] = {
                "crs": crs,
                "center": f"{center_lng:.8f},{center_lat:.8f}",
                "level": level,
                "w": width,
                "h": height,
                "maptype": maptype,
                "format": fmt,
                "scale": scale,
                "lang": lang,
            }
            if dataversion:
                params["dataversion"] = dataversion
            tiles.append(
                StaticMapTilePlan(
                    row=row,
                    col=col,
                    center=[round(center_lng, 8), round(center_lat, 8)],
                    bbox={
                        "min_lat": round(min_lat, 8),
                        "min_lng": round(min_lng, 8),
                        "max_lat": round(max_lat, 8),
                        "max_lng": round(max_lng, 8),
                    },
                    params=params,
                )
            )

    return {
        "schema": "arnis-korea-detailed.static_map_request_plan.v1",
        "endpoint": "https://maps.apigw.ntruss.com/map-static/v2/raster",
        "bbox": bbox,
        "level": level,
        "meters_per_pixel_estimate": round(mpp, 4),
        "estimated_bbox_size_m": {"width": round(bbox_w_m, 2), "height": round(bbox_h_m, 2)},
        "tile_pixel_size": {"w": width, "h": height, "scale": scale},
        "grid": {"rows": rows, "cols": cols, "request_count": rows * cols},
        "cost_estimate": {"static_map_requests": rows * cols},
        "tiles": [asdict(tile) for tile in tiles],
    }
