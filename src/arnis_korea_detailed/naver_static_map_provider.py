from __future__ import annotations

import hashlib
import os
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ENDPOINT = "https://maps.apigw.ntruss.com/map-static/v2/raster"
KEY_ID_FILE = Path.home() / ".config" / "arnis-korea" / "naver_client_id"
KEY_FILE = Path.home() / ".config" / "arnis-korea" / "naver_client_secret"


@dataclass
class SecretStatus:
    path: str
    exists: bool
    readable: bool
    length: int | None
    sha256_prefix: str | None


def _read_secret(path: Path) -> str | None:
    if not path.exists() or not os.access(path, os.R_OK):
        return None
    return path.read_text(encoding="utf-8").strip()


def secret_status(path: Path) -> SecretStatus:
    value = _read_secret(path)
    return SecretStatus(
        path=str(path),
        exists=path.exists(),
        readable=value is not None,
        length=len(value) if value is not None else None,
        sha256_prefix=hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value is not None else None,
    )


def key_file_status() -> dict[str, Any]:
    return {
        "key_id": secret_status(KEY_ID_FILE).__dict__,
        "key": secret_status(KEY_FILE).__dict__,
    }


def env_secret_status(name: str) -> dict[str, Any]:
    value = os.environ.get(name)
    return {
        "name": name,
        "exists": value is not None,
        "length": len(value) if value is not None else None,
        "sha256_prefix": hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value is not None else None,
    }


def key_source_status(key_id_file: Path | None = None, key_file: Path | None = None) -> dict[str, Any]:
    key_id_path = key_id_file or KEY_ID_FILE
    key_path = key_file or KEY_FILE
    return {
        "env": {
            "key_id": env_secret_status("NAVER_MAPS_CLIENT_ID"),
            "key": env_secret_status("NAVER_MAPS_CLIENT_SECRET"),
        },
        "file": {
            "key_id": secret_status(key_id_path).__dict__,
            "key": secret_status(key_path).__dict__,
        },
    }


def load_headers(key_id_file: Path | None = None, key_file: Path | None = None) -> dict[str, str] | None:
    key_id = os.environ.get("NAVER_MAPS_CLIENT_ID") or _read_secret(key_id_file or KEY_ID_FILE)
    key = os.environ.get("NAVER_MAPS_CLIENT_SECRET") or _read_secret(key_file or KEY_FILE)
    if not key_id or not key:
        return None
    return {
        "x-ncp-apigw-api-key-id": key_id,
        "x-ncp-apigw-api-key": key,
    }


def load_headers_from_files() -> dict[str, str] | None:
    return load_headers()


def build_static_map_url(params: dict[str, Any]) -> str:
    return f"{ENDPOINT}?{urllib.parse.urlencode(params)}"


def _hash_bytes(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256_prefix": hashlib.sha256(data).hexdigest()[:16]}


def probe_static_map(
    params: dict[str, Any],
    key_id_file: Path | None = None,
    key_file: Path | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    headers = load_headers(key_id_file, key_file)
    if headers is None:
        return {"executed": False, "reason": "missing_or_unreadable_keys", "key_status": key_source_status(key_id_file, key_file)}
    request = urllib.request.Request(build_static_map_url(params), headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return {
                "executed": True,
                "status": response.status,
                "content_type": response.headers.get("content-type"),
                **_hash_bytes(body),
                "saved": False,
            }
    except HTTPError as exc:
        body = exc.read()
        return {
            "executed": True,
            "status": exc.code,
            "content_type": exc.headers.get("content-type"),
            **_hash_bytes(body),
            "saved": False,
        }
    except Exception as exc:
        return {
            "executed": True,
            "status": "error",
            "error_type": type(exc).__name__,
            "saved": False,
        }


def download_static_map_if_allowed(
    params: dict[str, Any],
    output_path: Path,
    allow_storage: bool,
    allow_analysis: bool,
    key_id_file: Path | None = None,
    key_file: Path | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    if not (allow_storage and allow_analysis):
        return {
            "executed": False,
            "reason": "license_gate_blocks_static_raster_storage_or_analysis",
            "url_without_secrets": build_static_map_url(params),
            "key_status": key_source_status(key_id_file, key_file),
        }
    headers = load_headers(key_id_file, key_file)
    if headers is None:
        return {"executed": False, "reason": "missing_or_unreadable_keys", "key_status": key_source_status(key_id_file, key_file)}
    request = urllib.request.Request(build_static_map_url(params), headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)
        return {
            "executed": True,
            "status": response.status,
            "content_type": response.headers.get("content-type"),
            "size": len(data),
            "saved": True,
            "output_path": str(output_path),
        }
