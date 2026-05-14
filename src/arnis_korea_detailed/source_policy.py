from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OFFICIAL_NAVER_DOMAINS = {
    "maps.apigw.ntruss.com",
}

BLOCKED_EXTERNAL_SOURCES = {
    "overpass": "Overpass API",
    "openstreetmap": "OpenStreetMap API",
    "overture": "Overture Maps",
    "aws_terrain": "AWS Terrain Tiles",
    "esa_worldcover": "ESA WorldCover",
    "public_geodata": "public/government geodata",
    "naver_internal_tiles": "unofficial Naver internal map/tile endpoints",
}


@dataclass(frozen=True)
class SourcePolicy:
    name: str
    allowed_domains: tuple[str, ...]
    blocked_sources: tuple[str, ...]
    external_non_naver_sources_used: bool
    official_naver_api_only: bool
    no_network_renderer: bool

    def to_report(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "source_policy": self.name,
            "allowed_domains": list(self.allowed_domains),
            "blocked_sources": {key: BLOCKED_EXTERNAL_SOURCES[key] for key in self.blocked_sources},
            "external_non_naver_sources_used": self.external_non_naver_sources_used,
            "official_naver_api_only": self.official_naver_api_only,
            "renderer_no_network": self.no_network_renderer,
            **(extra or {}),
        }


NAVER_ONLY_POLICY = SourcePolicy(
    name="naver_only",
    allowed_domains=tuple(sorted(OFFICIAL_NAVER_DOMAINS)),
    blocked_sources=tuple(sorted(BLOCKED_EXTERNAL_SOURCES)),
    external_non_naver_sources_used=False,
    official_naver_api_only=True,
    no_network_renderer=True,
)


def policy_for_source(source: str) -> SourcePolicy:
    if source in {"naver-only", "mock-naver", "naver-static"}:
        return NAVER_ONLY_POLICY
    return SourcePolicy(
        name="legacy_or_hybrid",
        allowed_domains=(),
        blocked_sources=(),
        external_non_naver_sources_used=True,
        official_naver_api_only=False,
        no_network_renderer=False,
    )


def assert_naver_only_source(source: str) -> None:
    if source not in {"naver-only", "mock-naver", "naver-static"}:
        raise ValueError(f"source={source} is not allowed under naver_only policy")


def write_source_policy_report(path: Path, source: str, extra: dict[str, Any] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = policy_for_source(source).to_report(extra)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
