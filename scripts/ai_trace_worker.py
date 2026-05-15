#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arnis_korea_detailed.ai_trace.confidence_gate import passes_gate  # noqa: E402
from arnis_korea_detailed.ai_trace.cv_segmenter import segment_pixels  # noqa: E402
from arnis_korea_detailed.ai_trace.feature_vectorizer import vectorize_segments  # noqa: E402
from arnis_korea_detailed.ai_trace.geojson_writer import write_collection  # noqa: E402
from arnis_korea_detailed.ai_trace.quality_report import write_png_placeholder, write_report  # noqa: E402
from arnis_korea_detailed.ai_trace.raster_loader import find_raster, load_raster, raster_stats  # noqa: E402
from arnis_korea_detailed.trace_editor_core import read_json  # noqa: E402


def run_worker(package_dir: Path, output_dir: Path) -> dict[str, object]:
    package_dir = Path(package_dir)
    output_dir = Path(output_dir)
    project = read_json(package_dir / "project.arniskorea.json")
    bbox = project["bbox"]
    raster = find_raster(package_dir)
    width, height, pixels = load_raster(raster)
    segments = segment_pixels(width, height, pixels)
    features = vectorize_segments(width, height, bbox, segments)
    auto_accepted = []
    rejected = []
    suggested = []
    for item in features:
        props = item.setdefault("properties", {})
        layer = props.get("layer")
        confidence = float(props.get("confidence", 0))
        if passes_gate(str(layer), confidence):
            gated = json.loads(json.dumps(item))
            gated["properties"]["ai_trace_status"] = "auto_accepted_candidate"
            gated["properties"]["approved_by_user"] = False
            auto_accepted.append(gated)
            suggested.append(gated)
        else:
            props["ai_trace_status"] = "rejected_low_confidence"
            rejected.append(item)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_collection(output_dir / "suggested_layers.geojson", suggested + rejected)
    write_collection(output_dir / "auto_accepted_layers.geojson", auto_accepted)
    write_collection(output_dir / "rejected_low_confidence.geojson", rejected)
    write_png_placeholder(output_dir / "ai_trace_preview.png", 32, 32, (88, 140, 220))
    write_png_placeholder(output_dir / "confidence_heatmap.png", 32, 32, (220, 120, 80))
    report = {
        "schema_version": "arnis-korea.ai-trace-report.v2.0",
        "mode": "deterministic_cv",
        "windows_internal_model": False,
        "provider_used": False,
        "provider_fallback": "deterministic_cv",
        "source_policy": "naver_trace_editor_ai_trace_package",
        "external_non_naver_sources_used": False,
        "unofficial_naver_scraping_used": False,
        "raster": str(raster.name),
        "raster_stats": raster_stats(width, height, pixels),
        "suggested_count": len(suggested),
        "auto_accepted_candidate_count": len(auto_accepted),
        "rejected_low_confidence_count": len(rejected),
        "confidence_thresholds": {"road": 0.75, "water": 0.80, "green": 0.75, "building": 0.90},
    }
    write_report(output_dir / "ai_trace_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    report = run_worker(Path(args.package_dir), Path(args.output_dir))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
