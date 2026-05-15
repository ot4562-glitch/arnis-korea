from __future__ import annotations

from collections import defaultdict


def classify_ai_pixel(rgb: tuple[int, int, int]) -> str | None:
    r, g, b = rgb
    if b > 145 and b > r + 25 and b > g + 15:
        return "water"
    if g > 120 and g > r + 25 and g > b + 5:
        return "green"
    if abs(r - g) < 30 and abs(g - b) < 30 and 105 <= (r + g + b) / 3 <= 235:
        return "road"
    if 125 <= r <= 210 and 110 <= g <= 190 and 100 <= b <= 180 and abs(r - b) > 20:
        return "building"
    return None


def segment_pixels(width: int, height: int, pixels: list[tuple[int, int, int]]) -> dict[str, list[tuple[int, int]]]:
    stride = max(1, min(width, height) // 96)
    buckets: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for y in range(0, height, stride):
        for x in range(0, width, stride):
            kind = classify_ai_pixel(pixels[y * width + x])
            if kind:
                buckets[kind].append((x, y))
    return dict(buckets)
