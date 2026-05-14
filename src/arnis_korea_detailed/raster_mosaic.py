from __future__ import annotations

import struct
import zlib
from pathlib import Path


def read_ppm(path: Path) -> list[list[tuple[int, int, int]]]:
    tokens: list[str] = []
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith("#"):
            continue
        tokens.extend(line.split())
    if not tokens or tokens[0] != "P3":
        raise ValueError(f"{path} is not an ASCII PPM P3 file")
    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])
    if max_value != 255:
        raise ValueError("only max color value 255 is supported")
    values = [int(token) for token in tokens[4:]]
    if len(values) != width * height * 3:
        raise ValueError("PPM pixel count does not match header")
    pixels: list[list[tuple[int, int, int]]] = []
    index = 0
    for _ in range(height):
        row = []
        for _ in range(width):
            row.append((values[index], values[index + 1], values[index + 2]))
            index += 3
        pixels.append(row)
    return pixels


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path: Path) -> list[list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"{path} is not a PNG file")
    offset = 8
    width = height = bit_depth = color_type = None
    idat = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", chunk)
            if bit_depth != 8 or color_type not in {2, 6} or compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError("only non-interlaced 8-bit RGB/RGBA PNG is supported")
        elif chunk_type == b"IDAT":
            idat.extend(chunk)
        elif chunk_type == b"IEND":
            break
    if width is None or height is None or color_type is None:
        raise ValueError("PNG missing IHDR")
    channels = 4 if color_type == 6 else 3
    stride = width * channels
    raw = zlib.decompress(bytes(idat))
    rows: list[bytes] = []
    previous = bytearray(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        scanline = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        for i, value in enumerate(scanline):
            left = scanline[i - channels] if i >= channels else 0
            up = previous[i]
            upper_left = previous[i - channels] if i >= channels else 0
            if filter_type == 1:
                scanline[i] = (value + left) & 0xFF
            elif filter_type == 2:
                scanline[i] = (value + up) & 0xFF
            elif filter_type == 3:
                scanline[i] = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                scanline[i] = (value + _paeth(left, up, upper_left)) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"unsupported PNG filter type {filter_type}")
        rows.append(bytes(scanline))
        previous = scanline
    return [[tuple(row[x : x + 3]) for x in range(0, stride, channels)] for row in rows]


def single_image_mosaic(path: Path) -> list[list[tuple[int, int, int]]]:
    if path.suffix.lower() == ".png":
        return read_png(path)
    return read_ppm(path)
