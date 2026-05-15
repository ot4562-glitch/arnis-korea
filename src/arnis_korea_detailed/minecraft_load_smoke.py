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


DEFAULT_TARGET_MINECRAFT_VERSION = "26.1.2"
DEFAULT_TARGET_PAPER_API_VERSION = "26.1.2"
VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
PAPER_API_BASE = "https://api.papermc.io/v2/projects/paper"
PAPER_FILL_GRAPHQL = "https://fill.papermc.io/graphql"
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
    request = urllib.request.Request(url, headers={"User-Agent": "arnis-korea-minecraft-load-smoke/1.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_graphql(query: str) -> dict[str, Any]:
    request = urllib.request.Request(
        PAPER_FILL_GRAPHQL,
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "arnis-korea-minecraft-load-smoke/1.1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise ValueError(f"Paper Fill GraphQL error: {payload['errors'][0].get('message', 'unknown')}")
    return payload


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
        request = urllib.request.Request(info["url"], headers={"User-Agent": "arnis-korea-minecraft-load-smoke/1.1"})
        with urllib.request.urlopen(request, timeout=120) as response:
            path.write_bytes(response.read())
    return {**info, "path": str(path), "bytes": str(path.stat().st_size)}


def resolve_paper_download(version: str) -> dict[str, str]:
    fill_query = (
        '{ project(key:"paper") { version(key:"'
        + version
        + '") { key builds(first:1, orderBy:{direction: DESC}) { edges { node { number channel downloads { name url size checksums { sha256 } } } } } } } }'
    )
    try:
        payload = _read_graphql(fill_query)
        version_node = payload.get("data", {}).get("project", {}).get("version")
        edges = version_node.get("builds", {}).get("edges", []) if version_node else []
        if edges:
            node = edges[0]["node"]
            download = node.get("downloads", [])[0]
            return {
                "server_type": "paper",
                "version": version,
                "build": str(node.get("number")),
                "channel": str(node.get("channel", "")),
                "url": download["url"],
                "name": download["name"],
                "sha256": download.get("checksums", {}).get("sha256", ""),
            }
    except Exception:
        if version == DEFAULT_TARGET_PAPER_API_VERSION:
            raise
    builds_doc = _read_json_url(f"{PAPER_API_BASE}/versions/{version}/builds")
    builds = builds_doc.get("builds", [])
    if not builds:
        raise ValueError(f"Paper build not found for Minecraft version: {version}")
    build = builds[-1]
    build_number = str(build.get("build"))
    application = build.get("downloads", {}).get("application", {})
    name = application.get("name")
    sha256 = application.get("sha256", "")
    if not build_number or not name:
        raise ValueError(f"Paper download metadata incomplete for Minecraft version: {version}")
    return {
        "server_type": "paper",
        "version": version,
        "build": build_number,
        "url": f"{PAPER_API_BASE}/versions/{version}/builds/{build_number}/downloads/{name}",
        "name": name,
        "sha256": sha256,
    }


def download_paper_jar(path: Path, version: str, paper_api_version: str) -> dict[str, str]:
    info = resolve_paper_download(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        request = urllib.request.Request(info["url"], headers={"User-Agent": "arnis-korea-minecraft-load-smoke/1.1"})
        with urllib.request.urlopen(request, timeout=180) as response:
            path.write_bytes(response.read())
    return {**info, "target_paper_api_version": paper_api_version, "path": str(path), "bytes": str(path.stat().st_size)}


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
    paper_api_version: str = DEFAULT_TARGET_PAPER_API_VERSION,
    server_type: str = "paper",
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
    jar = server_jar or (output_dir / (f"paper-{target_version}.jar" if server_type == "paper" else f"minecraft-server-{target_version}.jar"))
    result: dict[str, Any] = {
        "schema": "arnis-korea.minecraft_load_smoke.v1",
        "world_dir": str(world_dir),
        "server_dir": str(server_dir),
        "target_minecraft_version": target_version,
        "target_server_type": server_type,
        "target_paper_api_version": paper_api_version,
        "timeout_seconds": timeout_seconds,
        "executed": True,
        "passed": False,
    }
    try:
        server_port = _find_free_port()
        result["server_port"] = server_port
        if server_jar is not None:
            download = {"path": str(jar), "version": target_version, "url": "provided", "server_type": server_type}
        elif server_type == "paper":
            download = download_paper_jar(jar, target_version, paper_api_version)
        else:
            download = download_server_jar(jar, target_version)
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
                "paper_26_1_2_gate": server_type == "paper" and paper_api_version == DEFAULT_TARGET_PAPER_API_VERSION,
                "passed": bool(done_seen and not fatal_hits and not crash_reports and (server_type != "paper" or paper_api_version == DEFAULT_TARGET_PAPER_API_VERSION)),
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
