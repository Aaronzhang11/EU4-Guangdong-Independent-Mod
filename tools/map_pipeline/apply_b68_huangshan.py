#!/usr/bin/env python3
"""Apply the guarded Huangshan mountain transplant and register its map consumers."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import shutil
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
PLAN = ROOT / "planning/huangshan_b68"
PROVINCES = MAP / "provinces.bmp"
BACKUP = PLAN / "pre_b68_provinces.bmp"
BEFORE = PLAN / "before_patch.png"
AFTER = PLAN / "after_patch.png"
REPORT = PLAN / "report.json"
PREVIEW = PLAN / "b68_applied_preview.png"
PATCH_BOX = (4624, 881, 4682, 926)
SOURCE_RGB = (22, 50, 32)
TARGET_RGB = (22, 50, 31)
MOUNTAIN_ID = 5380
MARKER = "GDD_B68_HUANGSHAN"
EXPECTED_COMPONENTS = [86, 71, 47]
TOUCHED_PLAYABLE_RGB = {
    (24, 170, 230),   # 4956 衢州
    (38, 197, 155),   # 4950 湖州
    (75, 175, 235),   # 5003 严州
    (97, 120, 255),   # 684 杭州
    (150, 42, 42),    # 2147 徽州
    (185, 197, 39),   # 2146 宁国
    (190, 91, 163),   # 5067 太平
    (231, 213, 161),  # 5326 德兴
}


def components(mask: np.ndarray) -> list[int]:
    seen = np.zeros(mask.shape, dtype=bool)
    sizes: list[int] = []
    for sy, sx in zip(*np.where(mask), strict=True):
        if seen[sy, sx]:
            continue
        stack = [(int(sy), int(sx))]
        seen[sy, sx] = True
        size = 0
        while stack:
            y, x = stack.pop()
            size += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        sizes.append(size)
    return sorted(sizes, reverse=True)


def bmp_layout(data: bytes) -> tuple[int, int, int, int, bool]:
    if data[:2] != b"BM":
        raise ValueError("provinces.bmp is not a BMP")
    offset = struct.unpack_from("<I", data, 10)[0]
    width = struct.unpack_from("<i", data, 18)[0]
    signed_height = struct.unpack_from("<i", data, 22)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    if width != 5632 or abs(signed_height) != 2048 or bpp != 24 or compression != 0:
        raise ValueError(f"unexpected BMP layout: {width}x{signed_height}, bpp={bpp}, compression={compression}")
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


def normalize_generated_assets() -> None:
    """Convert the builder's source RGB to the user-authoritative target RGB."""
    after = Image.open(AFTER).convert("RGBA")
    pixels = list(after.getdata())
    converted = 0
    output = []
    for r, g, b, a in pixels:
        if a and (r, g, b) == SOURCE_RGB:
            output.append((*TARGET_RGB, a))
            converted += 1
        else:
            output.append((r, g, b, a))
    if converted not in (0, 204):
        raise ValueError(f"unexpected source-colour count in guarded patch: {converted}")
    if converted:
        after.putdata(output)
        after.save(AFTER)

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    feature = report["features"][0]
    feature["source_rgb"] = list(SOURCE_RGB)
    feature["rgb"] = list(TARGET_RGB)
    feature["target_rgb"] = list(TARGET_RGB)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def guarded_pixels() -> list[tuple[int, int, tuple[int, int, int], tuple[int, int, int]]]:
    before = Image.open(BEFORE).convert("RGBA")
    after = Image.open(AFTER).convert("RGBA")
    expected_size = (PATCH_BOX[2] - PATCH_BOX[0], PATCH_BOX[3] - PATCH_BOX[1])
    if before.size != expected_size or after.size != expected_size:
        raise ValueError("guarded patch dimensions do not match the reviewed box")
    result = []
    for py in range(before.height):
        for px in range(before.width):
            br, bg, bb, ba = before.getpixel((px, py))
            ar, ag, ab, aa = after.getpixel((px, py))
            if ba != aa:
                raise ValueError("before/after alpha masks differ")
            if ba:
                result.append((PATCH_BOX[0] + px, PATCH_BOX[1] + py, (br, bg, bb), (ar, ag, ab)))
    if len(result) != 229:
        raise ValueError(f"expected 229 guarded pixels, found {len(result)}")
    return result


def apply_geometry() -> str:
    if not BACKUP.exists():
        shutil.copy2(PROVINCES, BACKUP)
    original = PROVINCES.read_bytes()
    header_size = struct.unpack_from("<I", original, 10)[0]
    header = original[:header_size]
    layout = bmp_layout(original)
    data = bytearray(original)
    states = []
    for x, y, before, after in guarded_pixels():
        current = read_pixel(data, x, y, layout)
        if current == before:
            states.append("before")
        elif current == after:
            states.append("after")
        else:
            raise ValueError(f"guard mismatch at ({x},{y}): {current}, expected {before} or {after}")
    if len(set(states)) > 1:
        raise ValueError("partially applied Huangshan patch; refusing mixed state")
    if states[0] == "before":
        for x, y, _before, after in guarded_pixels():
            write_pixel(data, x, y, after, layout)
        PROVINCES.write_bytes(data)
        if PROVINCES.read_bytes()[:header_size] != header:
            raise ValueError("BMP header changed while applying guarded pixels")
        return "applied"
    return "already_applied"


def block_bounds(text: str, name: str, start: int = 0, end: int | None = None) -> tuple[int, int]:
    limit = len(text) if end is None else end
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text[start:limit])
    if not match:
        raise ValueError(f"missing block {name}")
    block_start = start + match.start()
    opening = start + match.end() - 1
    depth = 0
    for index in range(opening, limit):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return block_start, index + 1
    raise ValueError(f"unclosed block {name}")


def marker_to_block(text: str, block: str, ids: tuple[int, ...], indent: str = "    ") -> str:
    text = re.sub(rf"(?m)^\s*.*# {MARKER}(?: .*)?\n?", "", text)
    start, end = block_bounds(text, block)
    insertion = text.rfind("}", start, end)
    return text[:insertion] + f"{indent}{' '.join(map(str, ids))} # {MARKER}\n" + text[insertion:]


def marker_to_nested_block(text: str, outer: str, inner: str, ids: tuple[int, ...]) -> str:
    text = re.sub(rf"(?m)^\s*.*# {MARKER}(?: .*)?\n?", "", text)
    outer_start, outer_end = block_bounds(text, outer)
    inner_start, inner_end = block_bounds(text, inner, outer_start, outer_end)
    insertion = text.rfind("}", inner_start, inner_end)
    return text[:insertion] + f"            {' '.join(map(str, ids))} # {MARKER}\n" + text[insertion:]


def update_consumers() -> None:
    definition = MAP / "definition.csv"
    lines = definition.read_text(encoding="latin-1").splitlines()
    for line in lines:
        fields = line.split(";")
        if len(fields) >= 4 and fields[0].isdigit():
            province_id = int(fields[0])
            rgb = tuple(map(int, fields[1:4]))
            if rgb == TARGET_RGB and province_id != MOUNTAIN_ID:
                raise ValueError(f"target RGB already belongs to province {province_id}")
    output = []
    found = False
    for line in lines:
        fields = line.split(";")
        if fields and fields[0] == str(MOUNTAIN_ID):
            output.append("5380;22;50;31;Huangshan;x")
            found = True
        else:
            output.append(line)
    if not found:
        output.append("5380;22;50;31;Huangshan;x")
    definition.write_text("\n".join(output) + "\n", encoding="latin-1")

    default = MAP / "default.map"
    text = default.read_text(encoding="latin-1")
    match = re.search(r"(?m)^max_provinces\s*=\s*(\d+)", text)
    if not match:
        raise ValueError("default.map lacks max_provinces")
    bound = max(int(match.group(1)), MOUNTAIN_ID + 1)
    default.write_text(re.sub(r"(?m)^max_provinces\s*=\s*\d+", f"max_provinces = {bound}", text), encoding="latin-1")

    climate = MAP / "climate.txt"
    climate.write_text(marker_to_block(climate.read_text(encoding="latin-1"), "impassable", (MOUNTAIN_ID,)), encoding="latin-1")
    continent = MAP / "continent.txt"
    continent.write_text(marker_to_block(continent.read_text(encoding="latin-1"), "asia", (MOUNTAIN_ID,), indent="        "), encoding="latin-1")
    terrain = MAP / "terrain.txt"
    terrain.write_text(marker_to_nested_block(terrain.read_text(encoding="latin-1"), "mountain", "terrain_override", (MOUNTAIN_ID,)), encoding="latin-1")


def update_localisation() -> None:
    source = MOD / "localisation_source/gdd_b16_anhui_map_readable_utf8.txt"
    text = source.read_text(encoding="utf-8-sig")
    text = re.sub(rf"(?m)^\s*PROV(?:_ADJ)?{MOUNTAIN_ID}:\d+\s+.*\n?", "", text)
    if not text.endswith("\n"):
        text += "\n"
    text += ' PROV5380:0 "黄山"\n PROV_ADJ5380:0 "黄山"\n'
    source.write_text(text, encoding="utf-8-sig")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(source, MOD / "localisation/gdd_b16_anhui_map_l_english.yml")


def render_preview(bitmap: np.ndarray) -> None:
    crop = PATCH_BOX
    zoom = 8
    panel = Image.fromarray(bitmap, mode="RGB").crop(crop).resize(
        ((crop[2] - crop[0]) * zoom, (crop[3] - crop[1]) * zoom), Image.Resampling.NEAREST
    )
    canvas = Image.new("RGB", (panel.width, panel.height + 60), (20, 25, 31))
    canvas.paste(panel, (0, 60))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 24)
    except OSError:
        font = ImageFont.load_default()
    draw.text((16, 15), "B68：黄山不可通行山脉（1:1）", font=font, fill=(240, 244, 248))
    canvas.save(PREVIEW)


def validate() -> np.ndarray:
    bitmap = np.array(Image.open(PROVINCES).convert("RGB"), dtype=np.uint8)
    mountain = np.all(bitmap == TARGET_RGB, axis=2)
    if int(mountain.sum()) != 204 or components(mountain) != EXPECTED_COMPONENTS:
        raise ValueError(f"unexpected Huangshan geometry: pixels={int(mountain.sum())}, components={components(mountain)}")
    for rgb in TOUCHED_PLAYABLE_RGB:
        sizes = components(np.all(bitmap == rgb, axis=2))
        if len(sizes) != 1:
            raise ValueError(f"touched playable RGB {rgb} is fragmented: {sizes}")

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("changed_pixels") != 229 or report.get("repaired_land_pixels") != 25:
        raise ValueError("guarded report does not match the reviewed transaction")
    return bitmap


def main() -> None:
    normalize_generated_assets()
    state = apply_geometry()
    update_consumers()
    update_localisation()
    bitmap = validate()
    render_preview(bitmap)
    print("B68_HUANGSHAN_OK " f"state={state} pixels=204 components=86,71,47 border_reflow=25 exterior=0")


if __name__ == "__main__":
    main()
