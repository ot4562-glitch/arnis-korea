from __future__ import annotations

import shutil
import struct
import zlib
from pathlib import Path
from typing import Any

from .korea_feature_schema import KoreaFeature
from .mock_raster_provider import PALETTE


CLASS_COLORS = {
    "background": (238, 238, 232),
    "road": (225, 225, 225),
    "road_major": (205, 205, 205),
    "road_minor": (220, 220, 220),
    "building": (210, 210, 205),
    "building_candidate": (210, 210, 205),
    "water": (65, 145, 220),
    "green": (90, 170, 95),
    "rail": (70, 70, 70),
    "label_noise": (255, 70, 70),
}


def write_png(path: Path, pixels: list[list[tuple[int, int, int]]]) -> Path:
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b in row:
            raw.extend((r, g, b))
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(bytes(raw)))
    data += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _mask(segments: list[list[str]], classes: set[str], color: tuple[int, int, int]) -> list[list[tuple[int, int, int]]]:
    return [[color if cls in classes else (245, 245, 245) for cls in row] for row in segments]


def _segmentation_preview(segments: list[list[str]]) -> list[list[tuple[int, int, int]]]:
    return [[CLASS_COLORS.get(cls, (238, 238, 232)) for cls in row] for row in segments]


def _pixel_to_lonlat(x: int, y: int, width: int, height: int, bbox: dict[str, float]) -> list[float]:
    lon = bbox["min_lng"] + (bbox["max_lng"] - bbox["min_lng"]) * (x / max(width - 1, 1))
    lat = bbox["max_lat"] - (bbox["max_lat"] - bbox["min_lat"]) * (y / max(height - 1, 1))
    return [lon, lat]


def _lonlat_to_pixel(point: list[float], bbox: dict[str, float], width: int, height: int) -> tuple[int, int]:
    lon, lat = point
    x = int(round((lon - bbox["min_lng"]) / max(bbox["max_lng"] - bbox["min_lng"], 1e-12) * (width - 1)))
    y = int(round((bbox["max_lat"] - lat) / max(bbox["max_lat"] - bbox["min_lat"], 1e-12) * (height - 1)))
    return max(0, min(width - 1, x)), max(0, min(height - 1, y))


def _draw_line(pixels: list[list[tuple[int, int, int]]], a: tuple[int, int], b: tuple[int, int], color: tuple[int, int, int], width: int = 2) -> None:
    height = len(pixels)
    image_width = len(pixels[0]) if height else 0
    steps = max(abs(b[0] - a[0]), abs(b[1] - a[1]), 1)
    radius = max(0, width // 2)
    for i in range(steps + 1):
        x = round(a[0] + (b[0] - a[0]) * i / steps)
        y = round(a[1] + (b[1] - a[1]) * i / steps)
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                px, py = x + dx, y + dy
                if 0 <= px < image_width and 0 <= py < height:
                    pixels[py][px] = color


def _draw_bbox(pixels: list[list[tuple[int, int, int]]], points: list[tuple[int, int]], color: tuple[int, int, int]) -> None:
    if not points:
        return
    min_x, max_x = min(x for x, _ in points), max(x for x, _ in points)
    min_y, max_y = min(y for _, y in points), max(y for _, y in points)
    for x in range(min_x, max_x + 1):
        if 0 <= x < len(pixels[0]):
            if 0 <= min_y < len(pixels):
                pixels[min_y][x] = color
            if 0 <= max_y < len(pixels):
                pixels[max_y][x] = color
    for y in range(min_y, max_y + 1):
        if 0 <= y < len(pixels):
            if 0 <= min_x < len(pixels[0]):
                pixels[y][min_x] = color
            if 0 <= max_x < len(pixels[0]):
                pixels[y][max_x] = color


def _overlay(base: list[list[tuple[int, int, int]]], features: list[KoreaFeature], bbox: dict[str, float]) -> list[list[tuple[int, int, int]]]:
    pixels = [[tuple(pixel) for pixel in row] for row in base]
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    for feature in features:
        color = CLASS_COLORS.get(feature.feature_class, (0, 0, 0))
        points = [_lonlat_to_pixel(point, bbox, width, height) for point in feature.coordinates]
        if feature.geometry_type == "line":
            for a, b in zip(points, points[1:]):
                _draw_line(pixels, a, b, color, 3 if feature.feature_class == "road" else 1)
        else:
            _draw_bbox(pixels, points, color)
    return pixels


def write_debug_previews(
    debug_dir: Path,
    raster_path: Path,
    pixels: list[list[tuple[int, int, int]]],
    segments: list[list[str]],
    features: list[KoreaFeature],
    bbox: dict[str, float],
) -> dict[str, str]:
    debug_dir.mkdir(parents=True, exist_ok=True)
    original = debug_dir / "original_static_map.png"
    if raster_path.suffix.lower() == ".png":
        shutil.copy2(raster_path, original)
    else:
        write_png(original, pixels)
    outputs = {
        "original_static_map": str(original),
        "segmentation_preview": str(write_png(debug_dir / "segmentation_preview.png", _segmentation_preview(segments))),
        "class_mask_roads": str(write_png(debug_dir / "class_mask_roads.png", _mask(segments, {"road", "road_major", "road_minor", "rail"}, (180, 180, 180)))),
        "class_mask_buildings": str(write_png(debug_dir / "class_mask_buildings.png", _mask(segments, {"building", "building_candidate"}, PALETTE["building"]))),
        "class_mask_green_water": str(write_png(debug_dir / "class_mask_green_water.png", _mask(segments, {"green", "water"}, (80, 170, 120)))),
        "world_overlay_preview": str(write_png(debug_dir / "world_overlay_preview.png", _overlay(pixels, features, bbox))),
    }
    return outputs
