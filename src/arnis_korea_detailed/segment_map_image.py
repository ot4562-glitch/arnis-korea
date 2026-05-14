from __future__ import annotations

from .mock_raster_provider import PALETTE


def _distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum((x - y) * (x - y) for x, y in zip(a, b))


def classify_pixel(pixel: tuple[int, int, int]) -> str:
    return min(PALETTE, key=lambda name: _distance(pixel, PALETTE[name]))


def segment_pixels(pixels: list[list[tuple[int, int, int]]]) -> list[list[str]]:
    return [[classify_pixel(pixel) for pixel in row] for row in pixels]
