#!/usr/bin/env python3
"""Register the user-drawn Zhe-Min and Wuyi impassable mountain provinces.

This transaction does not redraw provinces.bmp.  It verifies the two exact
RGB masks already present in the canonical bitmap, then registers all map
consumers and localisation required by EU4.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
PROVINCES = MAP / "provinces.bmp"
PLAN = ROOT / "planning/fujian_impassable_registration_b65"
BACKUP = PLAN / "pre_b65_provinces.bmp"
PREVIEW = PLAN / "b65_registered_preview.png"
MANIFEST = PLAN / "batch_manifest.json"

MARKER = "GDD_B65_FUJIAN_IMPASSABLE_REGISTRATION"
MAX_PROVINCES = 5380
MOUNTAINS = {
    5378: ((64, 130, 53), "Zhe-Min Mountains", "浙闽山脉"),
    5379: ((16, 71, 7), "Wuyi Mountains", "武夷山"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGB"), dtype=np.uint8, copy=True)


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


def bbox(mask: np.ndarray) -> list[int]:
    yy, xx = np.where(mask)
    return [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]


def block_bounds(text: str, name: str, start: int = 0, end: int | None = None) -> tuple[int, int]:
    limit = len(text) if end is None else end
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text[start:limit])
    if not match:
        raise ValueError(f"Missing block {name}")
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
    raise ValueError(f"Unclosed block {name}")


def remove_marker_lines(text: str) -> str:
    return re.sub(rf"(?m)^\s*.*# {MARKER}(?: .*)?\n?", "", text)


def add_marker_to_block(text: str, block: str, ids: tuple[int, ...], indent: str = "    ") -> str:
    text = remove_marker_lines(text)
    start, end = block_bounds(text, block)
    insertion = text.rfind("}", start, end)
    line = f"{indent}{' '.join(map(str, ids))} # {MARKER}\n"
    return text[:insertion] + line + text[insertion:]


def add_marker_to_nested_block(text: str, outer: str, inner: str, ids: tuple[int, ...]) -> str:
    text = remove_marker_lines(text)
    outer_start, outer_end = block_bounds(text, outer)
    inner_start, inner_end = block_bounds(text, inner, outer_start, outer_end)
    insertion = text.rfind("}", inner_start, inner_end)
    line = f"            {' '.join(map(str, ids))} # {MARKER}\n"
    return text[:insertion] + line + text[insertion:]


def validate_geometry(bitmap: np.ndarray) -> dict[str, object]:
    geometry: dict[str, object] = {}
    for province_id, (rgb, _english, chinese) in MOUNTAINS.items():
        mask = np.all(bitmap == rgb, axis=2)
        pixels = int(mask.sum())
        if pixels <= 0:
            raise ValueError(f"Province {province_id} / {chinese} RGB {rgb} has zero pixels")
        geometry[str(province_id)] = {
            "name": chinese,
            "rgb": list(rgb),
            "pixels": pixels,
            "bbox": bbox(mask),
            "components": components(mask),
            "component_policy": (
                "intentional_disconnected_mountain_segments"
                if province_id == 5378
                else "single_connected_mountain_body"
            ),
        }
    return geometry


def update_definitions() -> None:
    path = MAP / "definition.csv"
    lines = path.read_text(encoding="latin-1").splitlines()
    intended_colours = {province_id: data[0] for province_id, data in MOUNTAINS.items()}
    for line in lines:
        fields = line.split(";")
        if len(fields) < 4 or not fields[0].isdigit():
            continue
        province_id = int(fields[0])
        colour = tuple(map(int, fields[1:4]))
        for intended_id, intended_colour in intended_colours.items():
            if colour == intended_colour and province_id != intended_id:
                raise ValueError(f"RGB {intended_colour} already belongs to province {province_id}")
            if province_id == intended_id and colour != intended_colour:
                raise ValueError(f"Province ID {intended_id} already uses RGB {colour}")

    output: list[str] = []
    seen: set[int] = set()
    for line in lines:
        fields = line.split(";")
        if fields and fields[0].isdigit() and int(fields[0]) in MOUNTAINS:
            province_id = int(fields[0])
            colour, english, _chinese = MOUNTAINS[province_id]
            output.append(f"{province_id};{colour[0]};{colour[1]};{colour[2]};{english};x")
            seen.add(province_id)
        else:
            output.append(line)
    for province_id in sorted(set(MOUNTAINS) - seen):
        colour, english, _chinese = MOUNTAINS[province_id]
        output.append(f"{province_id};{colour[0]};{colour[1]};{colour[2]};{english};x")
    path.write_text("\n".join(output) + "\n", encoding="latin-1")


def update_map_consumers() -> None:
    ids = tuple(sorted(MOUNTAINS))
    default_path = MAP / "default.map"
    default_text = default_path.read_text(encoding="latin-1")
    match = re.search(r"(?m)^\s*max_provinces\s*=\s*(\d+)", default_text)
    if not match:
        raise ValueError("default.map has no max_provinces")
    bound = max(int(match.group(1)), MAX_PROVINCES)
    default_text = re.sub(r"(?m)^\s*max_provinces\s*=\s*\d+", f"max_provinces = {bound}", default_text)
    default_path.write_text(default_text, encoding="latin-1")

    climate = MAP / "climate.txt"
    climate.write_text(
        add_marker_to_block(climate.read_text(encoding="latin-1"), "impassable", ids),
        encoding="latin-1",
    )

    continent = MAP / "continent.txt"
    continent.write_text(
        add_marker_to_block(continent.read_text(encoding="latin-1"), "asia", ids, indent="        "),
        encoding="latin-1",
    )

    terrain = MAP / "terrain.txt"
    terrain.write_text(
        add_marker_to_nested_block(terrain.read_text(encoding="latin-1"), "mountain", "terrain_override", ids),
        encoding="latin-1",
    )


def update_localisation() -> None:
    source = MOD / "localisation_source/gdd_b19_fujian_map_readable_utf8.txt"
    text = source.read_text(encoding="utf-8-sig")
    for province_id in MOUNTAINS:
        text = re.sub(rf"(?m)^\s*PROV(?:_ADJ)?{province_id}:\d+\s+.*\n?", "", text)
    if not text.endswith("\n"):
        text += "\n"
    for province_id, (_rgb, _english, chinese) in sorted(MOUNTAINS.items()):
        text += f' PROV{province_id}:0 "{chinese}"\n PROV_ADJ{province_id}:0 "{chinese}"\n'
    source.write_text(text, encoding="utf-8-sig")

    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file

    encode_file(source, MOD / "localisation/gdd_b19_fujian_map_l_english.yml")


def render_preview(bitmap: np.ndarray) -> None:
    crop = (4580, 910, 4710, 1025)
    zoom = 5
    panel = Image.fromarray(bitmap).crop(crop).resize(
        ((crop[2] - crop[0]) * zoom, (crop[3] - crop[1]) * zoom),
        Image.Resampling.NEAREST,
    )
    canvas = Image.new("RGB", (panel.width, panel.height + 78), (20, 25, 31))
    canvas.paste(panel, (0, 78))
    draw = ImageDraw.Draw(canvas)
    try:
        title = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 24)
        detail = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 15)
    except OSError:
        title = detail = ImageFont.load_default()
    draw.text((18, 12), "B65：福建不可通行山脉注册", font=title, fill=(240, 244, 248))
    draw.text((18, 48), "浙闽山脉 64,130,53　　武夷山 16,71,7", font=detail, fill=(188, 245, 194))
    canvas.save(PREVIEW)


def main() -> None:
    PLAN.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(PROVINCES, BACKUP)
    bitmap = read_rgb(PROVINCES)
    before_hash = sha256(PROVINCES)
    geometry = validate_geometry(bitmap)
    update_definitions()
    update_map_consumers()
    update_localisation()
    if sha256(PROVINCES) != before_hash:
        raise RuntimeError("Registration unexpectedly changed provinces.bmp")
    render_preview(bitmap)
    MANIFEST.write_text(
        json.dumps(
            {
                "batch": "B65_fujian_impassable_registration",
                "marker": MARKER,
                "status": "implemented",
                "bitmap_geometry_source": "user_drawn_canonical_pixels",
                "bitmap_pixels_changed": 0,
                "connectivity_policy": {
                    "5378": "浙闽山脉保留用户绘制的多段山体，不进行人工连线",
                    "5379": "武夷山保持单一连通山体",
                },
                "backup": str(BACKUP),
                "canonical_bitmap_sha256": before_hash,
                "features": geometry,
                "consumers": {
                    "definition": sorted(MOUNTAINS),
                    "max_provinces": MAX_PROVINCES,
                    "climate_impassable": sorted(MOUNTAINS),
                    "terrain_mountain_override": sorted(MOUNTAINS),
                    "continent_asia": sorted(MOUNTAINS),
                    "localisation_source": "gdd_b19_fujian_map_readable_utf8.txt",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        "B65_FUJIAN_IMPASSABLE_REGISTRATION_APPLIED "
        f"ids={','.join(map(str, sorted(MOUNTAINS)))} bitmap_pixels_changed=0"
    )


if __name__ == "__main__":
    main()
