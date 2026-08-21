#!/usr/bin/env python3
"""Apply the guarded 1:1 Chaohu Lake transplant without rewriting the BMP header."""

from __future__ import annotations

import json
from pathlib import Path
import re
import struct
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
PLAN = ROOT / "planning/chaohu_lake_b67"
PROVINCES = MAP / "provinces.bmp"
BEFORE = PLAN / "before_patch.png"
AFTER = PLAN / "after_patch.png"
REPORT = PLAN / "report.json"
PATCH_BOX = (4638, 865, 4652, 874)
LAKE_ID = 4011
LAKE_RGB = (100, 14, 111)
PLAYABLE_RGB = (232, 181, 97)  # 5061 巢湖


def bmp_layout(data: bytes) -> tuple[int, int, int, int, bool]:
    if data[:2] != b"BM":
        raise ValueError("provinces.bmp is not a BMP")
    offset = struct.unpack_from("<I", data, 10)[0]
    width = struct.unpack_from("<i", data, 18)[0]
    signed_height = struct.unpack_from("<i", data, 22)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    if width != 5632 or abs(signed_height) != 2048 or bpp != 24 or compression != 0:
        raise ValueError(
            f"unexpected BMP layout: {width}x{signed_height}, bpp={bpp}, compression={compression}"
        )
    stride = ((width * 3 + 3) // 4) * 4
    return offset, width, abs(signed_height), stride, signed_height > 0


def read_pixel(data: bytes | bytearray, x: int, y: int, layout: tuple[int, int, int, int, bool]) -> tuple[int, int, int]:
    offset, _width, height, stride, bottom_up = layout
    row = height - 1 - y if bottom_up else y
    pos = offset + row * stride + x * 3
    b, g, r = data[pos : pos + 3]
    return r, g, b


def write_pixel(data: bytearray, x: int, y: int, rgb: tuple[int, int, int], layout: tuple[int, int, int, int, bool]) -> None:
    offset, _width, height, stride, bottom_up = layout
    row = height - 1 - y if bottom_up else y
    pos = offset + row * stride + x * 3
    r, g, b = rgb
    data[pos : pos + 3] = bytes((b, g, r))


def patch_pixels() -> list[tuple[int, int, tuple[int, int, int], tuple[int, int, int]]]:
    if not BEFORE.exists() or not AFTER.exists():
        raise ValueError("guarded patch assets are missing")
    before = Image.open(BEFORE).convert("RGBA")
    after = Image.open(AFTER).convert("RGBA")
    expected_size = (PATCH_BOX[2] - PATCH_BOX[0], PATCH_BOX[3] - PATCH_BOX[1])
    if before.size != expected_size or after.size != expected_size:
        raise ValueError(f"unexpected patch size: {before.size} / {after.size}")
    result = []
    for py in range(before.height):
        for px in range(before.width):
            br, bg, bb, ba = before.getpixel((px, py))
            ar, ag, ab, aa = after.getpixel((px, py))
            if ba != aa:
                raise ValueError("before/after alpha masks differ")
            if ba:
                result.append((PATCH_BOX[0] + px, PATCH_BOX[1] + py, (br, bg, bb), (ar, ag, ab)))
    if len(result) != 22:
        raise ValueError(f"expected 22 guarded lake pixels, found {len(result)}")
    return result


def apply_bitmap() -> str:
    original = PROVINCES.read_bytes()
    header = original[:138]
    layout = bmp_layout(original)
    data = bytearray(original)
    state = []
    for x, y, before, after in patch_pixels():
        current = read_pixel(data, x, y, layout)
        if current == before:
            state.append("before")
        elif current == after:
            state.append("after")
        else:
            raise ValueError(f"guard mismatch at ({x},{y}): {current}, expected {before} or {after}")
    if len(set(state)) > 1:
        raise ValueError("partially applied Chaohu patch; refusing mixed state")
    if state[0] == "before":
        for x, y, _before, after in patch_pixels():
            write_pixel(data, x, y, after, layout)
        PROVINCES.write_bytes(data)
        if PROVINCES.read_bytes()[:138] != header:
            raise ValueError("BMP header changed while applying pixel patch")
        return "applied"
    return "already_applied"


def update_definition() -> None:
    path = MAP / "definition.csv"
    output = []
    found = False
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if fields and fields[0] == str(LAKE_ID):
            output.append(f"{LAKE_ID};100;14;111;Chaohu Lake;x")
            found = True
        else:
            output.append(line)
    if not found:
        raise ValueError("reserved lake ID 4011 is absent from definition.csv")
    path.write_text("\n".join(output) + "\n", encoding="latin-1")


def update_localisation() -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file

    encode_file(
        MOD / "localisation_source/gdd_b16_anhui_map_readable_utf8.txt",
        MOD / "localisation/gdd_b16_anhui_map_l_english.yml",
    )


def validate() -> None:
    data = PROVINCES.read_bytes()
    layout = bmp_layout(data)
    lake_pixels = 0
    playable_pixels = 0
    for y in range(layout[2]):
        for x in range(layout[1]):
            rgb = read_pixel(data, x, y, layout)
            lake_pixels += rgb == LAKE_RGB
            playable_pixels += rgb == PLAYABLE_RGB
    if lake_pixels != 22:
        raise ValueError(f"expected exactly 22 Chaohu pixels, found {lake_pixels}")
    if playable_pixels != 142:
        raise ValueError(f"unexpected remaining playable Chaohu pixels: {playable_pixels}")

    default = (MAP / "default.map").read_text(encoding="latin-1")
    match = re.search(r"(?ms)^lakes\s*=\s*\{(.*?)^\}", default)
    if not match or not re.search(r"(?<!\d)4011(?!\d)", match.group(1)):
        raise ValueError("4011 is not registered in default.map lakes")

    definition = (MAP / "definition.csv").read_text(encoding="latin-1")
    if "4011;100;14;111;Chaohu Lake;x" not in definition:
        raise ValueError("Chaohu definition is not registered")

    source = (MOD / "localisation_source/gdd_b16_anhui_map_readable_utf8.txt").read_text(encoding="utf-8-sig")
    for key in ('PROV4011:0 "巢湖"', 'PROV_ADJ4011:0 "巢湖"'):
        if key not in source:
            raise ValueError(f"missing localisation: {key}")

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("changed_pixels") != 22:
        raise ValueError("guarded patch report does not describe 22 pixels")


def main() -> None:
    state = apply_bitmap()
    update_definition()
    update_localisation()
    validate()
    print(f"B67_CHAOHU_LAKE_OK state={state} lake_id=4011 pixels=22 playable_5061=142")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"B67_CHAOHU_LAKE_FAILED: {exc}", file=sys.stderr)
        raise
