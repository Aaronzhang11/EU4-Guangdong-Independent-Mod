#!/usr/bin/env python3
"""Apply the reviewed Guangdong impassable-mountain guarded patch.

The transaction reuses 5310/5311 with user-specified RGBs and allocates 5377
for Jiulian Mountains.  It applies only opaque reviewed pixels and accepts
either the recorded before value or the already-applied after value, making
the geometry step idempotent without replacing unrelated map work.
"""

from __future__ import annotations

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
PLAN = ROOT / "planning/guangdong_impassable_dmi_plan"
PATCH = PLAN / "aligned_patch"
IMPLEMENTATION = PLAN / "implementation_b64"
PROVINCES = MAP / "provinces.bmp"
BACKUP = IMPLEMENTATION / "pre_b64_provinces.bmp"
PREVIEW = IMPLEMENTATION / "b64_applied_preview.png"
MANIFEST = IMPLEMENTATION / "batch_manifest.json"
BEFORE_PATCH = PATCH / "before_patch.png"
AFTER_PATCH = PATCH / "after_patch.png"
PATCH_REPORT = PATCH / "report.json"

MARKER = "GDD_B64_GUANGDONG_IMPASSABLE_MOUNTAINS"
JIULIAN_ID = 5377
MAX_PROVINCES = 5378
MOUNTAINS = {
    5310: ((48, 63, 86), "Nanling West", "南岭西段"),
    5311: ((118, 0, 175), "Nanling East", "南岭东段"),
    JIULIAN_ID: ((24, 11, 27), "Jiulian Mountains", "九连山"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGB"), dtype=np.uint8, copy=True)


def load_patch(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with Image.open(path) as image:
        rgba = np.array(image.convert("RGBA"), dtype=np.uint8, copy=True)
    return rgba[:, :, :3], rgba[:, :, 3] == 255


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


def add_marker_to_block(text: str, block: str, ids: tuple[int, ...], indent: str = "    ") -> str:
    text = re.sub(rf"(?m)^\s*.*# {MARKER}(?: .*)?\n?", "", text)
    start, end = block_bounds(text, block)
    insertion = text.rfind("}", start, end)
    line = f"{indent}{' '.join(map(str, ids))} # {MARKER}\n"
    return text[:insertion] + line + text[insertion:]


def add_marker_to_nested_block(text: str, outer: str, inner: str, ids: tuple[int, ...]) -> str:
    text = re.sub(rf"(?m)^\s*.*# {MARKER}(?: .*)?\n?", "", text)
    outer_start, outer_end = block_bounds(text, outer)
    inner_start, inner_end = block_bounds(text, inner, outer_start, outer_end)
    insertion = text.rfind("}", inner_start, inner_end)
    line = f"            {' '.join(map(str, ids))} # {MARKER}\n"
    return text[:insertion] + line + text[insertion:]


def apply_geometry() -> tuple[np.ndarray, int, tuple[int, int, int, int]]:
    report = json.loads(PATCH_REPORT.read_text(encoding="utf-8"))
    patch_box = tuple(report["final_patch_box"])
    before_values, before_mask = load_patch(BEFORE_PATCH)
    after_values, after_mask = load_patch(AFTER_PATCH)
    if not np.array_equal(before_mask, after_mask):
        raise ValueError("Before/after patch alpha masks differ")

    current = read_rgb(PROVINCES)
    x0, y0, x1, y1 = patch_box
    target = current[y0:y1, x0:x1]
    if target.shape[:2] != after_mask.shape:
        raise ValueError("Guarded patch dimensions do not match the canonical bitmap")
    current_pixels = target[after_mask]
    before_pixels = before_values[after_mask]
    after_pixels = after_values[after_mask]
    allowed = np.all(current_pixels == before_pixels, axis=1) | np.all(current_pixels == after_pixels, axis=1)
    if not np.all(allowed):
        unexpected = np.where(~allowed)[0][:10]
        raise ValueError(f"Guarded patch overlaps later map edits at editable indices {unexpected.tolist()}")

    changed_now = int(np.any(current_pixels != after_pixels, axis=1).sum())
    target[after_mask] = after_pixels
    Image.fromarray(current, mode="RGB").save(PROVINCES, format="BMP")
    return current, changed_now, patch_box


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
                raise ValueError(f"RGB {intended_colour} is already assigned to province {province_id}")

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
    default_path = MAP / "default.map"
    default_text = default_path.read_text(encoding="latin-1")
    match = re.search(r"(?m)^\s*max_provinces\s*=\s*(\d+)", default_text)
    if not match:
        raise ValueError("default.map has no max_provinces")
    bound = max(int(match.group(1)), MAX_PROVINCES)
    default_text = re.sub(r"(?m)^\s*max_provinces\s*=\s*\d+", f"max_provinces = {bound}", default_text)
    default_path.write_text(default_text, encoding="latin-1")

    climate_path = MAP / "climate.txt"
    climate_path.write_text(
        add_marker_to_block(climate_path.read_text(encoding="latin-1"), "impassable", (JIULIAN_ID,)),
        encoding="latin-1",
    )

    continent_path = MAP / "continent.txt"
    continent_path.write_text(
        add_marker_to_block(continent_path.read_text(encoding="latin-1"), "asia", (JIULIAN_ID,), indent="        "),
        encoding="latin-1",
    )

    terrain_path = MAP / "terrain.txt"
    terrain_path.write_text(
        add_marker_to_nested_block(
            terrain_path.read_text(encoding="latin-1"),
            "mountain",
            "terrain_override",
            (JIULIAN_ID,),
        ),
        encoding="latin-1",
    )


def update_localisation() -> None:
    source = MOD / "localisation_source/gdd_b30_yuebei_chaoshan_map_readable_utf8.txt"
    text = source.read_text(encoding="utf-8-sig")
    text = re.sub(rf"(?m)^\s*PROV(?:_ADJ)?{JIULIAN_ID}:\d+\s+.*\n?", "", text)
    if not text.endswith("\n"):
        text += "\n"
    text += f' PROV{JIULIAN_ID}:0 "九连山"\n PROV_ADJ{JIULIAN_ID}:0 "九连山"\n'
    source.write_text(text, encoding="utf-8-sig")

    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file

    encode_file(source, MOD / "localisation/gdd_b30_yuebei_chaoshan_map_l_english.yml")


def render_preview(bitmap: np.ndarray) -> None:
    crop = (4480, 930, 4660, 1080)
    zoom = 4
    panel = Image.fromarray(bitmap).crop(crop).resize(
        ((crop[2] - crop[0]) * zoom, (crop[3] - crop[1]) * zoom),
        Image.Resampling.NEAREST,
    )
    canvas = Image.new("RGB", (panel.width, panel.height + 62), (20, 25, 31))
    canvas.paste(panel, (0, 62))
    draw = ImageDraw.Draw(canvas)
    try:
        title = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 25)
    except OSError:
        title = ImageFont.load_default()
    draw.text((18, 16), "B64：南岭与九连山（实装图）", font=title, fill=(240, 244, 248))
    canvas.save(PREVIEW)


def write_manifest(changed_now: int, patch_box: tuple[int, int, int, int], bitmap: np.ndarray) -> None:
    geometry = {
        str(province_id): {
            "name": chinese,
            "rgb": list(colour),
            "pixels": int(np.all(bitmap == colour, axis=2).sum()),
        }
        for province_id, (colour, _english, chinese) in MOUNTAINS.items()
    }
    MANIFEST.write_text(
        json.dumps(
            {
                "batch": "B64_guangdong_impassable_mountains",
                "marker": MARKER,
                "status": "implemented_unvalidated_by_user_request",
                "guarded_patch_box": list(patch_box),
                "guarded_patch_editable_pixels": 674,
                "pixels_changed_this_run": changed_now,
                "backup": str(BACKUP),
                "canonical_bitmap_sha256": sha256(PROVINCES),
                "features": geometry,
                "consumers": {
                    "definition": [5310, 5311, JIULIAN_ID],
                    "max_provinces": MAX_PROVINCES,
                    "climate_impassable": [5310, 5311, JIULIAN_ID],
                    "terrain_mountain_override": [5310, 5311, JIULIAN_ID],
                    "continent_asia": [5310, 5311, JIULIAN_ID],
                    "localisation_source": "gdd_b30_yuebei_chaoshan_map_readable_utf8.txt",
                },
                "static_validation": "deferred by user request",
                "in_game_validation": "not run",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    IMPLEMENTATION.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(PROVINCES, BACKUP)
    if not BEFORE_PATCH.exists() or not AFTER_PATCH.exists() or not PATCH_REPORT.exists():
        raise SystemExit("Reviewed guarded patch assets are missing")

    bitmap, changed_now, patch_box = apply_geometry()
    update_definitions()
    update_map_consumers()
    update_localisation()
    render_preview(bitmap)
    write_manifest(changed_now, patch_box, bitmap)
    print(
        "B64_GUANGDONG_IMPASSABLE_MOUNTAINS_APPLIED "
        f"changed_pixels_this_run={changed_now} jiulian_id={JIULIAN_ID} "
        "static_validation=deferred"
    )


if __name__ == "__main__":
    main()
