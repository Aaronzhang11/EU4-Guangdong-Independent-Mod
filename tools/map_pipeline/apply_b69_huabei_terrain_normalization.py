#!/usr/bin/env python3
"""Normalize anomalous North China terrain in script and graphical terrain."""

from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
MOD_ROOT = REPO_ROOT / "guangdong_independent_practice"
MAP_ROOT = MOD_ROOT / "map"
PLAN_ROOT = REPO_ROOT / "planning/huabei_terrain_b69"
TERRAIN_PATH = MAP_ROOT / "terrain.txt"
TERRAIN_BITMAP = MAP_ROOT / "terrain.bmp"
PROVINCES_BITMAP = MAP_ROOT / "provinces.bmp"
DEFINITION_PATH = MAP_ROOT / "definition.csv"
TERRAIN_BACKUP = PLAN_ROOT / "pre_b69_terrain.bmp"
BITMAP_REPORT = PLAN_ROOT / "terrain_bitmap_report.json"

FARMLANDS_INDEX = 11
HILLS_INDEX = 1
PRESERVED_INDICES = (15, 17, 35)  # ocean, inland ocean and coastline

FARMLANDS = (
    5115, 5116, 5212, 5222, 5223, 5219, 5221, 5220,
    5101, 5102, 5103, 5111, 5104, 5107, 5109, 5110,
)
HILLS = (5113, 5114, 5211, 5213, 5218, 5105, 5106, 5108, 5112)

FARMLANDS_MARKER = "GDD_B69_HUABEI_TERRAIN_FARMLANDS"
HILLS_MARKER = "GDD_B69_HUABEI_TERRAIN_HILLS"


def definition_colours(ids: tuple[int, ...]) -> dict[int, tuple[int, int, int]]:
    wanted = set(ids)
    result: dict[int, tuple[int, int, int]] = {}
    with DEFINITION_PATH.open(encoding="latin-1", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if not row or not row[0].isdigit():
                continue
            province_id = int(row[0])
            if province_id not in wanted:
                continue
            if province_id in result:
                raise RuntimeError(f"Duplicate definition row for province {province_id}")
            result[province_id] = tuple(map(int, row[1:4]))
    missing = sorted(wanted - result.keys())
    if missing:
        raise RuntimeError(f"Missing definition rows: {missing}")
    return result


def apply_terrain_bitmap() -> dict[str, int]:
    PLAN_ROOT.mkdir(parents=True, exist_ok=True)
    if not TERRAIN_BACKUP.exists():
        shutil.copy2(TERRAIN_BITMAP, TERRAIN_BACKUP)

    with Image.open(PROVINCES_BITMAP) as image:
        provinces = np.array(image.convert("RGB"), dtype=np.uint8)
    with Image.open(TERRAIN_BITMAP) as image:
        if image.mode != "P":
            raise RuntimeError(f"terrain.bmp must be paletted, found {image.mode}")
        terrain = np.array(image, dtype=np.uint8)
        palette = image.getpalette()
        dpi = image.info.get("dpi", (96, 96))
    if provinces.shape[:2] != terrain.shape:
        raise RuntimeError("provinces.bmp and terrain.bmp dimensions differ")

    colours = definition_colours(FARMLANDS + HILLS)
    editable = np.zeros(terrain.shape, dtype=bool)
    changed_this_run = 0
    preserved_coastline = 0
    target_pixels: dict[int, int] = {}

    for province_id, desired_index in (
        *((province_id, FARMLANDS_INDEX) for province_id in FARMLANDS),
        *((province_id, HILLS_INDEX) for province_id in HILLS),
    ):
        colour = np.array(colours[province_id], dtype=np.uint8)
        province_mask = np.all(provinces == colour, axis=2)
        pixel_count = int(province_mask.sum())
        if pixel_count == 0:
            raise RuntimeError(f"Province {province_id} has no pixels")
        target_pixels[province_id] = pixel_count
        editable |= province_mask
        preserved = province_mask & np.isin(terrain, PRESERVED_INDICES)
        paintable = province_mask & ~preserved
        changed_this_run += int(np.count_nonzero(terrain[paintable] != desired_index))
        preserved_coastline += int(np.count_nonzero(province_mask & (terrain == 35)))
        terrain[paintable] = desired_index

    output = Image.fromarray(terrain, mode="P")
    output.putpalette(palette)
    output.save(TERRAIN_BITMAP, format="BMP", dpi=dpi)

    with Image.open(TERRAIN_BITMAP) as image:
        if image.mode != "P" or image.size != (terrain.shape[1], terrain.shape[0]):
            raise RuntimeError("terrain.bmp mode or dimensions changed")
        if image.getpalette() != palette:
            raise RuntimeError("terrain.bmp palette changed")
        written = np.array(image, dtype=np.uint8)
    with Image.open(TERRAIN_BACKUP) as image:
        baseline = np.array(image, dtype=np.uint8)
    if baseline.shape != written.shape:
        raise RuntimeError("terrain bitmap backup dimensions differ")
    exterior_changes = int(np.count_nonzero((written != baseline) & ~editable))
    if exterior_changes:
        raise RuntimeError(f"Found {exterior_changes} terrain changes outside target provinces")

    for province_id, desired_index in (
        *((province_id, FARMLANDS_INDEX) for province_id in FARMLANDS),
        *((province_id, HILLS_INDEX) for province_id in HILLS),
    ):
        province_mask = np.all(provinces == np.array(colours[province_id], dtype=np.uint8), axis=2)
        validate_mask = province_mask & ~np.isin(written, PRESERVED_INDICES)
        values = np.unique(written[validate_mask])
        if values.tolist() != [desired_index]:
            raise RuntimeError(
                f"Province {province_id} graphical terrain mismatch: {values.tolist()}"
            )

    result = {
        "changed_this_run": changed_this_run,
        "changed_from_backup": int(np.count_nonzero(written != baseline)),
        "exterior_changed_pixels": exterior_changes,
        "preserved_coastline_pixels": preserved_coastline,
        "target_province_pixels": sum(target_pixels.values()),
    }
    BITMAP_REPORT.write_text(
        json.dumps(
            {
                "batch": "B69_HUABEI_TERRAIN_NORMALIZATION",
                "farmlands_index": FARMLANDS_INDEX,
                "hills_index": HILLS_INDEX,
                "preserved_indices": list(PRESERVED_INDICES),
                **result,
                "province_pixels": {str(key): value for key, value in target_pixels.items()},
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return result


def block_span(text: str, name: str, start: int = 0) -> tuple[int, int]:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text[start:])
    if not match:
        raise RuntimeError(f"Missing block: {name}")
    begin = start + match.start()
    opening = text.find("{", start + match.start(), start + match.end())
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return begin, index + 1
    raise RuntimeError(f"Unclosed block: {name}")


def category_span(text: str, category: str) -> tuple[int, int]:
    categories_start, categories_end = block_span(text, "categories")
    relative_start, relative_end = block_span(
        text[categories_start:categories_end], category
    )
    return categories_start + relative_start, categories_start + relative_end


def insert_override(text: str, category: str, ids: tuple[int, ...], marker: str) -> str:
    category_start, category_end = category_span(text, category)
    category_text = text[category_start:category_end]
    override_start, override_end = block_span(category_text, "terrain_override")
    absolute_end = category_start + override_end
    closing_brace = text.rfind("}", category_start + override_start, absolute_end)
    closing_line_start = text.rfind("\n", 0, closing_brace) + 1
    payload = f"            {' '.join(map(str, ids))} # {marker}\n"
    # Normalize the nested block's closing indentation as part of the replay.
    return text[:closing_line_start] + payload + "        " + text[closing_brace:]


def override_memberships(text: str) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    categories_start, categories_end = block_span(text, "categories")
    categories_text = text[categories_start:categories_end]
    category_pattern = re.compile(r"(?m)^\s{4}([a-z_]+)\s*=\s*\{")
    for match in category_pattern.finditer(categories_text):
        category = match.group(1)
        start, end = block_span(categories_text, category, match.start())
        category_text = categories_text[start:end]
        try:
            override_start, override_end = block_span(category_text, "terrain_override")
        except RuntimeError:
            continue
        override = category_text[override_start:override_end]
        override = re.sub(r"#.*", "", override)
        for token in re.findall(r"(?<!\d)\d+(?!\d)", override):
            result.setdefault(int(token), []).append(category)
    return result


def main() -> None:
    bitmap_result = apply_terrain_bitmap()
    text = TERRAIN_PATH.read_text(encoding="latin-1")
    text = "\n".join(
        line for line in text.splitlines()
        if FARMLANDS_MARKER not in line and HILLS_MARKER not in line
    ) + "\n"

    existing = override_memberships(text)
    targets = FARMLANDS + HILLS
    conflicts = {province_id: existing[province_id] for province_id in targets if province_id in existing}
    if conflicts:
        raise RuntimeError(f"Target provinces already have terrain overrides: {conflicts}")

    text = insert_override(text, "farmlands", FARMLANDS, FARMLANDS_MARKER)
    text = insert_override(text, "hills", HILLS, HILLS_MARKER)

    memberships = override_memberships(text)
    expected = {province_id: ["farmlands"] for province_id in FARMLANDS}
    expected.update({province_id: ["hills"] for province_id in HILLS})
    actual = {province_id: memberships.get(province_id, []) for province_id in targets}
    if actual != expected:
        raise RuntimeError(f"Terrain override validation failed: {actual}")

    TERRAIN_PATH.write_text(text, encoding="latin-1")
    print(f"Updated {TERRAIN_PATH}")
    print("Farmlands:", " ".join(map(str, FARMLANDS)))
    print("Hills:", " ".join(map(str, HILLS)))
    print("terrain.bmp:", bitmap_result)


if __name__ == "__main__":
    main()
