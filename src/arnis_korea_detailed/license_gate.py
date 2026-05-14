from __future__ import annotations

from enum import Enum


class LicenseGate(str, Enum):
    USE_UI_ONLY = "USE_UI_ONLY"
    USE_GEOCODING_ONLY = "USE_GEOCODING_ONLY"
    USE_STATIC_RASTER_ANALYSIS_ALLOWED = "USE_STATIC_RASTER_ANALYSIS_ALLOWED"
    CONTRACT_REQUIRED = "CONTRACT_REQUIRED"
    FORBIDDEN_OR_UNCLEAR = "FORBIDDEN_OR_UNCLEAR"


DEFAULT_NAVER_GATE = LicenseGate.CONTRACT_REQUIRED


def static_raster_allowed(allow_storage: bool, allow_analysis: bool) -> bool:
    return allow_storage and allow_analysis


def assert_source_allowed(source_mode: str, gate: LicenseGate = DEFAULT_NAVER_GATE) -> None:
    if source_mode == "naver_disabled":
        raise RuntimeError("Naver provider is intentionally disabled until license review passes.")
    if source_mode in {"mock_raster", "osm_only", "public_data_stub"}:
        return
    if gate != LicenseGate.USE_STATIC_RASTER_ANALYSIS_ALLOWED:
        raise RuntimeError(f"source_mode={source_mode} is blocked by license_gate={gate.value}")
