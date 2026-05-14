from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_WORLD_NAME = "Arnis Korea Naver World"
PROJECT_DIR_NAME = "arnis_korea_project"


@dataclass(frozen=True)
class OutputLayout:
    output_dir: Path
    world_dir: Path
    metadata_dir: Path
    world_name: str


def sanitize_world_name(value: str | None) -> str:
    name = (value or DEFAULT_WORLD_NAME).strip() or DEFAULT_WORLD_NAME
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name.rstrip(" .") or DEFAULT_WORLD_NAME


def build_output_layout(output_dir: Path, world_name: str | None = None, project_metadata_dir: Path | None = None) -> OutputLayout:
    root = output_dir.resolve()
    clean_world_name = sanitize_world_name(world_name)
    metadata_dir = (project_metadata_dir.resolve() if project_metadata_dir else root / PROJECT_DIR_NAME)
    return OutputLayout(
        output_dir=root,
        world_dir=root / clean_world_name,
        metadata_dir=metadata_dir,
        world_name=clean_world_name,
    )
