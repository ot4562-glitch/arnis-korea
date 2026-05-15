from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_TARGET_MINECRAFT_VERSION = "1.21.1"
VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
FATAL_PATTERNS = [
    "Exception reading",
    "Failed to load level",
    "Failed to load chunk",
    "Failed to read chunk",
    "ChunkLoadError",
    "Reported exception",
    "Crash report",
    "java.lang.NullPointerException",
    "java.lang.IllegalArgumentException",
    "level.dat",
    "r.0.0.mca",
]


def _read_json_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "arnis-korea-minecraft-load-smoke/0.7"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve_server_download(version: str) -> dict[str, str]:
    manifest = _read_json_url(VERSION_MANIFEST_URL)
    match = next((item for item in manifest.get("versions", []) if item.get("id") == version), None)
    if not match:
        raise ValueError(f"Minecraft version not found in Mojang manifest: {version}")
    version_doc = _read_json_url(match["url"])
    server = version_doc.get("downloads", {}).get("server", {})
    if not server.get("url"):
        raise ValueError(f"Minecraft server download not available for version: {version}")
    return {"version": version, "url": server["url"], "sha1": server.get("sha1", "")}


def download_server_jar(path: Path, version: str) -> dict[str, str]:
    info = resolve_server_download(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        request = urllib.request.Request(info["url"], headers={"User-Agent": "arnis-korea-minecraft-load-smoke/0.7"})
        with urllib.request.urlopen(request, timeout=120) as response:
            path.write_bytes(response.read())
    return {**info, "path": str(path), "bytes": str(path.stat().st_size)}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write_server_files(server_dir: Path, server_port: int) -> None:
    (server_dir / "eula.txt").write_text("eula=true\n", encoding="ascii")
    (server_dir / "server.properties").write_text(
        "\n".join(
            [
                "online-mode=false",
                "enable-command-block=false",
                "spawn-protection=0",
                "view-distance=4",
                "simulation-distance=4",
                "level-name=world",
                f"server-port={server_port}",
                "enable-query=false",
                "enable-rcon=false",
                "motd=Arnis Korea load smoke",
            ]
        )
        + "\n",
        encoding="ascii",
    )


def _copy_world(world_dir: Path, server_dir: Path) -> Path:
    target = server_dir / "world"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(world_dir, target, ignore=shutil.ignore_patterns("*.json", "*.md", "debug", "logs", "naver_raster"))
    return target


def _tail(path: Path, chars: int = 12000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[-chars:]


def _has_done(log_text: str) -> bool:
    return "Done (" in log_text or "Done." in log_text or "For help, type" in log_text


def _fatal_hits(log_text: str) -> list[str]:
    lowered = log_text.lower()
    hits = []
    for pattern in FATAL_PATTERNS:
        low = pattern.lower()
        if low in lowered and not (low == "level.dat" and "preparing level" in lowered):
            hits.append(pattern)
    return sorted(set(hits))


def run_minecraft_load_smoke(
    world_dir: Path,
    output_dir: Path,
    server_jar: Path | None = None,
    target_version: str = DEFAULT_TARGET_MINECRAFT_VERSION,
    timeout_seconds: int = 180,
    java_bin: str = "java",
) -> dict[str, Any]:
    world_dir = world_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    server_dir = output_dir / "server"
    if server_dir.exists():
        shutil.rmtree(server_dir)
    server_dir.mkdir(parents=True, exist_ok=True)
    jar = server_jar or (output_dir / f"minecraft-server-{target_version}.jar")
    result: dict[str, Any] = {
        "schema": "arnis-korea.minecraft_load_smoke.v1",
        "world_dir": str(world_dir),
        "server_dir": str(server_dir),
        "target_minecraft_version": target_version,
        "timeout_seconds": timeout_seconds,
        "executed": True,
        "passed": False,
    }
    try:
        server_port = _find_free_port()
        result["server_port"] = server_port
        download = download_server_jar(jar, target_version) if server_jar is None else {"path": str(jar), "version": target_version, "url": "provided"}
        result["server_download"] = download
        copied_world = _copy_world(world_dir, server_dir)
        result["copied_world_dir"] = str(copied_world)
        _write_server_files(server_dir, server_port)
        log_path = server_dir / "logs" / "latest.log"
        command = [java_bin, "-Xmx2G", "-Xms1G", "-jar", str(jar), "nogui"]
        result["command"] = command
        process = subprocess.Popen(
            command,
            cwd=server_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "JAVA_TOOL_OPTIONS": os.environ.get("JAVA_TOOL_OPTIONS", "")},
        )
        output_lines: list[str] = []
        start = time.monotonic()
        done_seen = False
        while time.monotonic() - start < timeout_seconds:
            if process.stdout is None:
                break
            line = process.stdout.readline()
            if line:
                output_lines.append(line)
                joined = "".join(output_lines[-200:])
                if _has_done(joined):
                    done_seen = True
                    break
            elif process.poll() is not None:
                break
            else:
                time.sleep(0.2)
        if process.stdin:
            try:
                process.stdin.write("stop\n")
                process.stdin.flush()
            except Exception:
                pass
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        stdout_tail = "".join(output_lines)[-12000:]
        log_tail = _tail(log_path)
        combined = stdout_tail + "\n" + log_tail
        crash_reports = sorted(str(path) for path in (server_dir / "crash-reports").glob("*.txt")) if (server_dir / "crash-reports").is_dir() else []
        fatal_hits = _fatal_hits(combined)
        result.update(
            {
                "returncode": process.returncode,
                "done_seen": done_seen,
                "latest_log": str(log_path),
                "stdout_tail": stdout_tail,
                "latest_log_tail": log_tail,
                "fatal_log_patterns": fatal_hits,
                "crash_reports": crash_reports,
                "passed": bool(done_seen and not fatal_hits and not crash_reports),
            }
        )
    except Exception as exc:
        result.update(
            {
                "passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "infrastructure_failure": "download" in str(exc).lower() or "url" in str(exc).lower(),
            }
        )
    (output_dir / "minecraft_load_smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
