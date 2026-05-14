from __future__ import annotations

import gzip
import json
import math
import struct
import time
import zlib
from pathlib import Path
from typing import Any


DATA_VERSION = 3955
GROUND_Y = 64

BLOCKS = {
    "air": "minecraft:air",
    "bedrock": "minecraft:bedrock",
    "dirt": "minecraft:dirt",
    "grass_block": "minecraft:grass_block",
    "gray_concrete": "minecraft:gray_concrete",
    "black_concrete": "minecraft:black_concrete",
    "light_gray_concrete": "minecraft:light_gray_concrete",
    "stone_bricks": "minecraft:stone_bricks",
    "bricks": "minecraft:bricks",
    "smooth_stone": "minecraft:smooth_stone",
    "water": "minecraft:water",
    "iron_block": "minecraft:iron_block",
}


def _name(name: str) -> bytes:
    raw = name.encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


def _tag(tag_id: int, name: str, payload: bytes) -> bytes:
    return bytes([tag_id]) + _name(name) + payload


def _byte(value: int) -> bytes:
    return struct.pack(">b", value)


def _int(value: int) -> bytes:
    return struct.pack(">i", value)


def _long(value: int) -> bytes:
    return struct.pack(">q", value)


def _float(value: float) -> bytes:
    return struct.pack(">f", value)


def _double(value: float) -> bytes:
    return struct.pack(">d", value)


def _string(value: str) -> bytes:
    return _name(value)


def _long_array(values: list[int]) -> bytes:
    return _int(len(values)) + b"".join(_long(v) for v in values)


def _int_array(values: list[int]) -> bytes:
    return _int(len(values)) + b"".join(_int(v) for v in values)


def _list(tag_id: int, items: list[bytes]) -> bytes:
    return bytes([tag_id]) + _int(len(items)) + b"".join(items)


def _compound_payload(items: list[bytes]) -> bytes:
    return b"".join(items) + b"\x00"


def _compound_tag(name: str, items: list[bytes]) -> bytes:
    return _tag(10, name, _compound_payload(items))


def _root_compound(items: list[bytes]) -> bytes:
    return _compound_tag("", items)


def _to_signed_64(value: int) -> int:
    value &= (1 << 64) - 1
    return value - (1 << 64) if value >= (1 << 63) else value


def _pack_indices(indices: list[int], bits: int = 4) -> list[int]:
    values_per_long = 64 // bits
    mask = (1 << bits) - 1
    packed: list[int] = []
    for offset in range(0, len(indices), values_per_long):
        value = 0
        for bit_index, index in enumerate(indices[offset : offset + values_per_long]):
            value |= (index & mask) << (bit_index * bits)
        packed.append(_to_signed_64(value))
    return packed


def _pack_heightmap(height: int) -> list[int]:
    values: list[int] = [height for _ in range(256)]
    bits = 9
    packed: list[int] = []
    current = 0
    used = 0
    for value in values:
        current |= value << used
        used += bits
        while used >= 64:
            packed.append(_to_signed_64(current))
            current = value >> (bits - (used - 64)) if used > 64 else 0
            used -= 64
    if used:
        packed.append(_to_signed_64(current))
    return packed


def _palette_compound(block_name: str) -> bytes:
    return _compound_payload([_tag(8, "Name", _string(block_name))])


def _empty_section(y: int) -> bytes:
    return _compound_payload(
        [
            _tag(1, "Y", _byte(y)),
            _compound_tag("block_states", [_tag(9, "palette", _list(10, [_palette_compound(BLOCKS["air"])]))]),
            _compound_tag("biomes", [_tag(9, "palette", _list(8, [_string("minecraft:plains")]))]),
        ]
    )


def _section(y: int, blocks: list[str]) -> bytes:
    palette_names = sorted({BLOCKS[name] for name in blocks})
    if BLOCKS["air"] in palette_names:
        palette_names.remove(BLOCKS["air"])
        palette_names.insert(0, BLOCKS["air"])
    palette_index = {name: index for index, name in enumerate(palette_names)}
    indices = [palette_index[BLOCKS[name]] for name in blocks]
    block_state_items = [_tag(9, "palette", _list(10, [_palette_compound(name) for name in palette_names]))]
    if len(palette_names) > 1:
        block_state_items.append(_tag(12, "data", _long_array(_pack_indices(indices))))
    return _compound_payload(
        [
            _tag(1, "Y", _byte(y)),
            _compound_tag("block_states", block_state_items),
            _compound_tag("biomes", [_tag(9, "palette", _list(8, [_string("minecraft:plains")]))]),
        ]
    )


def _chunk_nbt(chunk_x: int, chunk_z: int, column_blocks: dict[tuple[int, int, int], str]) -> bytes:
    sections: list[bytes] = []
    for section_y in range(-4, 20):
        blocks = ["air"] * 4096
        has_content = False
        for y in range(section_y * 16, section_y * 16 + 16):
            for z in range(16):
                for x in range(16):
                    world_key = (chunk_x * 16 + x, y, chunk_z * 16 + z)
                    name = column_blocks.get(world_key)
                    if name:
                        blocks[(y - section_y * 16) * 256 + z * 16 + x] = name
                        has_content = True
        sections.append(_section(section_y, blocks) if has_content else _empty_section(section_y))
    height = GROUND_Y - (-64) + 1
    heightmap = _long_array(_pack_heightmap(height))
    return _root_compound(
        [
            _tag(3, "DataVersion", _int(DATA_VERSION)),
            _tag(3, "xPos", _int(chunk_x)),
            _tag(3, "yPos", _int(-4)),
            _tag(3, "zPos", _int(chunk_z)),
            _tag(8, "Status", _string("minecraft:full")),
            _tag(1, "isLightOn", _byte(0)),
            _tag(4, "InhabitedTime", _long(0)),
            _tag(4, "LastUpdate", _long(0)),
            _tag(9, "sections", _list(10, sections)),
            _compound_tag(
                "Heightmaps",
                [
                    _tag(12, "MOTION_BLOCKING", heightmap),
                    _tag(12, "MOTION_BLOCKING_NO_LEAVES", heightmap),
                    _tag(12, "OCEAN_FLOOR", heightmap),
                    _tag(12, "WORLD_SURFACE", heightmap),
                ],
            ),
            _compound_tag("structures", [_compound_tag("References", []), _compound_tag("starts", [])]),
            _tag(9, "PostProcessing", _list(9, [_list(10, []) for _ in range(24)])),
            _tag(9, "block_ticks", _list(10, [])),
            _tag(9, "fluid_ticks", _list(10, [])),
            _tag(9, "block_entities", _list(10, [])),
            _tag(9, "entities", _list(10, [])),
        ]
    )


def _write_level_dat(output_dir: Path, world_name: str, spawn_x: int, spawn_z: int) -> None:
    now = int(time.time() * 1000)
    data = _compound_tag(
        "Data",
        [
            _tag(3, "DataVersion", _int(DATA_VERSION)),
            _tag(4, "LastPlayed", _long(now)),
            _tag(8, "LevelName", _string(world_name)),
            _tag(3, "GameType", _int(1)),
            _tag(1, "hardcore", _byte(0)),
            _tag(1, "allowCommands", _byte(1)),
            _tag(3, "SpawnX", _int(spawn_x)),
            _tag(3, "SpawnY", _int(GROUND_Y + 2)),
            _tag(3, "SpawnZ", _int(spawn_z)),
            _tag(1, "initialized", _byte(1)),
            _tag(8, "Difficulty", _string("normal")),
            _tag(4, "RandomSeed", _long(0)),
            _compound_tag("Version", [_tag(8, "Name", _string("1.21.1")), _tag(3, "Id", _int(DATA_VERSION)), _tag(1, "Snapshot", _byte(0))]),
            _compound_tag("DataPacks", [_tag(9, "Enabled", _list(8, [_string("vanilla")])), _tag(9, "Disabled", _list(8, []))]),
            _tag(9, "Player", _list(10, [])),
        ],
    )
    (output_dir / "level.dat").write_bytes(gzip.compress(_root_compound([data])))


def _lonlat_to_world(point: list[float], bbox: dict[str, float], size: int) -> tuple[int, int]:
    lon, lat = point
    x_ratio = (lon - bbox["min_lng"]) / max(bbox["max_lng"] - bbox["min_lng"], 1e-12)
    z_ratio = (bbox["max_lat"] - lat) / max(bbox["max_lat"] - bbox["min_lat"], 1e-12)
    return (max(0, min(size - 1, int(round(x_ratio * (size - 1))))), max(0, min(size - 1, int(round(z_ratio * (size - 1))))))


def _draw_line(blocks: dict[tuple[int, int, int], str], a: tuple[int, int], b: tuple[int, int], block: str, width: int) -> None:
    x0, z0 = a
    x1, z1 = b
    steps = max(abs(x1 - x0), abs(z1 - z0), 1)
    radius = max(0, width // 2)
    for i in range(steps + 1):
        x = round(x0 + (x1 - x0) * i / steps)
        z = round(z0 + (z1 - z0) * i / steps)
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                blocks[(x + dx, GROUND_Y + 1, z + dz)] = block


def _fill_bbox(blocks: dict[tuple[int, int, int], str], points: list[tuple[int, int]], block: str, height: int = 1) -> None:
    if not points:
        return
    min_x, max_x = min(x for x, _ in points), max(x for x, _ in points)
    min_z, max_z = min(z for _, z in points), max(z for _, z in points)
    for x in range(min_x, max_x + 1):
        for z in range(min_z, max_z + 1):
            for y in range(GROUND_Y + 1, GROUND_Y + 1 + height):
                blocks[(x, y, z)] = block


def _blocks_from_features(world_doc: dict[str, Any], bbox: dict[str, float], size: int) -> dict[tuple[int, int, int], str]:
    blocks: dict[tuple[int, int, int], str] = {}
    for x in range(size):
        for z in range(size):
            blocks[(x, GROUND_Y - 2, z)] = "bedrock"
            blocks[(x, GROUND_Y - 1, z)] = "dirt"
            blocks[(x, GROUND_Y, z)] = "grass_block"
    for feature in world_doc.get("features", []):
        points = [_lonlat_to_world(point, bbox, size) for point in feature.get("coordinates", [])]
        hint = feature.get("world_hint", {})
        cls = feature.get("class")
        if not points:
            continue
        if feature.get("geometry_type") == "line":
            width = int(hint.get("width", 2))
            block = str(hint.get("block", "gray_concrete"))
            for a, b in zip(points, points[1:]):
                _draw_line(blocks, a, b, block, width)
        elif cls in {"building", "building_candidate", "campus_area"}:
            _fill_bbox(blocks, points, str(hint.get("block", "stone_bricks")), int(hint.get("height", 8)))
        elif cls == "water":
            _fill_bbox(blocks, points, "water", 1)
        elif cls == "green":
            _fill_bbox(blocks, points, "grass_block", 1)
    return blocks


def _write_region(output_dir: Path, blocks: dict[tuple[int, int, int], str], size: int) -> Path:
    region_dir = output_dir / "region"
    region_dir.mkdir(parents=True, exist_ok=True)
    region_path = region_dir / "r.0.0.mca"
    chunks_per_axis = max(1, math.ceil(size / 16))
    payloads: dict[tuple[int, int], bytes] = {}
    for chunk_x in range(chunks_per_axis):
        for chunk_z in range(chunks_per_axis):
            nbt = _chunk_nbt(chunk_x, chunk_z, blocks)
            compressed = zlib.compress(nbt)
            payloads[(chunk_x, chunk_z)] = bytes([2]) + compressed

    header_locations = bytearray(4096)
    header_timestamps = bytearray(4096)
    sectors = [bytes(8192)]
    sector_offset = 2
    for (chunk_x, chunk_z), payload in payloads.items():
        length = len(payload) + 4
        chunk = struct.pack(">I", length) + payload
        sector_count = math.ceil(len(chunk) / 4096)
        padded = chunk + b"\x00" * (sector_count * 4096 - len(chunk))
        sectors.append(padded)
        index = chunk_x + chunk_z * 32
        header_locations[index * 4 : index * 4 + 4] = struct.pack(">I", (sector_offset << 8) | sector_count)
        header_timestamps[index * 4 : index * 4 + 4] = struct.pack(">I", int(time.time()))
        sector_offset += sector_count
    sectors[0] = bytes(header_locations + header_timestamps)
    region_path.write_bytes(b"".join(sectors))
    return region_path


def write_world(
    output_dir: Path,
    world_features_path: Path,
    bbox: dict[str, float],
    source_mode: str,
    terrain_source: str,
    building_mode: str,
    size: int = 128,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    world_doc = json.loads(world_features_path.read_text(encoding="utf-8"))
    blocks = _blocks_from_features(world_doc, bbox, size)
    region_path = _write_region(output_dir, blocks, size)
    _write_level_dat(output_dir, "Arnis Korea Naver-only", size // 2, size // 2)
    report = {
        "world_generated": True,
        "writer": "arnis_korea_minimal_anvil_writer",
        "renderer_no_network": True,
        "source_mode": source_mode,
        "terrain_source": terrain_source,
        "external_dem_used": False,
        "height_source": "heuristic_from_naver_raster",
        "exact_height_available": False,
        "building_mode": building_mode,
        "level_dat": str(output_dir / "level.dat"),
        "region_file": str(region_path),
        "mca_count": len(list((output_dir / "region").glob("*.mca"))),
        "feature_count": len(world_doc.get("features", [])),
    }
    (output_dir / "arnis-korea-quality-report.md").write_text(
        "\n".join(
            [
                "# Arnis Korea v0.5 Naver-only Quality Report",
                "",
                f"- source_mode: {source_mode}",
                f"- writer: {report['writer']}",
                f"- renderer_no_network: {str(report['renderer_no_network']).lower()}",
                f"- external_non_naver_sources_used: false",
                f"- terrain_source: {terrain_source}",
                f"- external_dem_used: false",
                f"- height_source: {report['height_source']}",
                f"- exact_height_available: false",
                f"- feature_count: {report['feature_count']}",
                f"- mca_count: {report['mca_count']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return report
