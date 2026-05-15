#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arnis_korea_detailed.minecraft_load_smoke import DEFAULT_TARGET_MINECRAFT_VERSION, run_minecraft_load_smoke


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a temporary Minecraft Java server load smoke for a generated world.")
    parser.add_argument("--world-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--server-jar", type=Path)
    parser.add_argument("--target-minecraft-version", default=DEFAULT_TARGET_MINECRAFT_VERSION)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--java-bin", default="java")
    args = parser.parse_args()
    result = run_minecraft_load_smoke(
        args.world_dir,
        args.output_dir,
        server_jar=args.server_jar,
        target_version=args.target_minecraft_version,
        timeout_seconds=args.timeout_seconds,
        java_bin=args.java_bin,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
