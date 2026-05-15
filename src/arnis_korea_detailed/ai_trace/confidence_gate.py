from __future__ import annotations

THRESHOLDS = {"road": 0.75, "water": 0.80, "green": 0.75, "building": 0.90}


def confidence_for(kind: str, points: list[tuple[int, int]], width: int, height: int) -> float:
    coverage = min(1.0, len(points) / max(1, (width * height) / 900))
    base = {"road": 0.78, "water": 0.84, "green": 0.80, "building": 0.62}.get(kind, 0.5)
    return round(min(0.96, base + coverage * 0.12), 3)


def passes_gate(kind: str, confidence: float) -> bool:
    return confidence >= THRESHOLDS.get(kind, 1.0)
