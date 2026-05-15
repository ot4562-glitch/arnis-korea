from __future__ import annotations

from pathlib import Path


PALETTE = {
    "background": (238, 238, 232),
    "road": (245, 245, 245),
    "building": (190, 170, 150),
    "water": (90, 160, 220),
    "green": (110, 175, 105),
    "rail": (80, 80, 80),
    "label_noise": (25, 25, 25),
}


def generate_mock_pixels(width: int = 96, height: int = 96) -> list[list[tuple[int, int, int]]]:
    pixels = [[PALETTE["background"] for _ in range(width)] for _ in range(height)]

    for y in range(height):
        for x in range(width):
            if 42 <= x <= 50 or 45 <= y <= 53:
                pixels[y][x] = PALETTE["road"]
            if 8 <= x <= 31 and 10 <= y <= 31:
                pixels[y][x] = PALETTE["building"]
            if 61 <= x <= 84 and 9 <= y <= 35:
                pixels[y][x] = PALETTE["building"]
            if 12 <= x <= 34 and 63 <= y <= 84:
                pixels[y][x] = PALETTE["green"]
            if 58 <= x <= 88 and 63 <= y <= 82:
                pixels[y][x] = PALETTE["water"]
            if abs(y - (x // 2 + 18)) <= 1 and 0 <= x < width:
                pixels[y][x] = PALETTE["rail"]
            if (x, y) in {(5, 5), (6, 5), (16, 44), (17, 44), (18, 44), (73, 52), (73, 53), (74, 53)}:
                pixels[y][x] = PALETTE["label_noise"]

    return pixels


def write_ppm(path: Path, pixels: list[list[tuple[int, int, int]]]) -> None:
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    with path.open("w", encoding="ascii") as handle:
        handle.write(f"P3\n{width} {height}\n255\n")
        for row in pixels:
            handle.write(" ".join(f"{r} {g} {b}" for r, g, b in row))
            handle.write("\n")


def create_mock_raster(path: Path, width: int = 96, height: int = 96) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_ppm(path, generate_mock_pixels(width, height))
    return path
