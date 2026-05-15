from __future__ import annotations

from pathlib import Path
from typing import Any


def load_raster(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    path = Path(path)
    if path.suffix.lower() == ".ppm":
        from arnis_korea_detailed.trace_editor_core import read_ppm

        return read_ppm(path)
    try:
        from PIL import Image  # type: ignore
    except Exception as exc:
        raise ValueError("PNG/JPEG raster 분석에는 OCI worker 환경의 Pillow가 필요합니다. mock QA는 PPM을 지원합니다.") from exc
    image = Image.open(path).convert("RGB")
    width, height = image.size
    return width, height, list(image.getdata())


def find_raster(package_dir: Path) -> Path:
    candidates = []
    for name in ("raster.png", "static-map-000.png", "mock_background.ppm"):
        candidate = package_dir / name
        if candidate.exists():
            candidates.append(candidate)
    candidates.extend(sorted((package_dir / "naver_raster").glob("*.png")) if (package_dir / "naver_raster").is_dir() else [])
    candidates.extend(sorted(package_dir.glob("*.ppm")))
    if not candidates:
        raise FileNotFoundError("AI Trace package에서 raster 파일을 찾지 못했습니다.")
    return candidates[0]


def raster_stats(width: int, height: int, pixels: list[tuple[int, int, int]]) -> dict[str, Any]:
    sample = pixels[:: max(1, len(pixels) // 512)] or pixels[:1]
    avg = [sum(pixel[i] for pixel in sample) / max(1, len(sample)) for i in range(3)]
    return {"width": width, "height": height, "sample_count": len(sample), "avg_rgb": [round(value, 2) for value in avg]}
