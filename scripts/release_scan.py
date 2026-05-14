#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

BINARY_SUFFIXES = {".exe", ".dll", ".so", ".dylib", ".a", ".rlib", ".gz", ".zip", ".png", ".ppm", ".jpg", ".jpeg", ".gif", ".icns", ".ico", ".mca", ".dat"}
SKIP_PARTS = {".git", "target", "__pycache__", "upstream", "bin"}

POLICY_PATTERNS = [
    "p" + "static",
    r"(?<!oapi\.)" + "map" + r"\." + "naver" + r"\.com",
    "x" + "/" + "y" + "/" + "z",
    "quad" + "key",
    "sele" + "nium",
    "play" + "wright",
    "pupp" + "eteer",
    "screen" + "shot",
    "to" + "Data" + "URL",
    "dev" + "tools",
    r"\b" + "H" + "AR" + r"\b",
    "inter" + "cept",
    r"\b" + "scr" + "ape" + r"\b",
    r"\b" + "cr" + "awl" + r"\b",
    r"\b" + "by" + "pass" + r"\b",
    r"\b" + "sp" + "oof" + r"\b",
]


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.name == "release_scan.py":
            continue
        if path.suffix in BINARY_SUFFIXES:
            continue
        yield path


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    compiled = re.compile("|".join(POLICY_PATTERNS), re.IGNORECASE)
    hits = []
    for path in iter_text_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in compiled.finditer(text):
            hits.append(f"{path}: {match.group(0)}")
    if hits:
        print("UNOFFICIAL_NAVER_RETRIEVAL_SCAN=FAIL")
        print("\n".join(hits[:50]))
        return 1
    print("UNOFFICIAL_NAVER_RETRIEVAL_SCAN=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
