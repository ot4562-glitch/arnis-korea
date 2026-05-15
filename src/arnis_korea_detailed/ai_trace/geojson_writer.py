from __future__ import annotations

from pathlib import Path
from typing import Any

from arnis_korea_detailed.trace_editor_core import LAYER_SCHEMA_VERSION, write_json


def collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "schema_version": LAYER_SCHEMA_VERSION, "features": features}


def write_collection(path: Path, features: list[dict[str, Any]]) -> dict[str, Any]:
    data = collection(features)
    write_json(path, data)
    return data
