#!/usr/bin/env python3
"""Repair fragmented Huai-bank provinces and stale river crossings.

The navigable Huai predates the B47 southern-Henan redraw.  B47 changed the
land masks around Runing, Xizhou and Guangzhou without rebuilding the special
adjacency table, leaving long-distance or geometrically invalid "sea" links.
The original water cut also left Huai'an split across both banks and several
one-pixel land crumbs near Hongze Lake and the estuary.

This terminal transaction is deliberately narrow and idempotent.  It changes
only reviewed pixels, rebuilds every crossing through the seven Huai water
provinces, and validates four-way province connectivity and water contact.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / "guangdong_independent_practice/map"
OUT = ROOT / "planning/huai_connectivity_b75"
MARKER = "GDD_B75_HUAI_CONNECTIVITY_REPAIR"

PROVINCES = MAP / "provinces.bmp"
HEIGHTMAP = MAP / "heightmap.bmp"
RIVERS = MAP / "rivers.bmp"
ADJACENCIES = MAP / "adjacencies.csv"
REPORT = OUT / "report.json"
PREVIEW = OUT / "preview.png"

HUAI_WATERS = {5039, 5040, 5041, 5042, 1896, 5043, 5044}

# The northern pre-B47 half of Huai'an is reassigned to neighbouring Suqian.
# Huai'an keeps the eastern component containing its city and port.
HUAIAN_TO_SUQIAN = (
    (827, 4658, 4662),
    (828, 4658, 4665),
    (829, 4657, 4667),
    (830, 4656, 4665),
    (831, 4655, 4664),
    (832, 4654, 4664),
    (833, 4653, 4663),
    (834, 4652, 4662),
    (835, 4651, 4653),
    (835, 4656, 4656),
    (835, 4659, 4660),
    (836, 4650, 4652),
    (837, 4650, 4651),
    (838, 4651, 4651),
)

# (x, y, source province, target province).  These are isolated crumbs whose
# target touches the pixel orthogonally in the reviewed canonical geometry.
PIXEL_REASSIGNMENTS = (
    (4659, 843, 2142, 5117),  # Huai'an crumb -> Hangou
    (4659, 845, 2142, 5117),
    (4650, 842, 2143, 1896),  # Haozhou crumb -> Hongze Lake
    (4628, 846, 2143, 5041),  # Haozhou crumb -> Yingshou Reach
    (4675, 826, 4196, 5020),  # Haizhou estuary crumbs -> Yancheng
    (4676, 826, 4196, 5020),
    (4677, 825, 4196, 5020),
    (4674, 827, 4196, 5020),
)

# Local crossings only.  Every endpoint is required to touch its Through
# water province after the pixel repair.
CROSSINGS = (
    (5054, 2175, 5039, "Runing-Xinyang Huai crossing"),
    (5349, 5350, 5040, "Xizhou-Guangzhou Huai crossing"),
    (2144, 5059, 5040, "Yingzhou-Shouzhou Huai crossing"),
    (2143, 5064, 5041, "Haozhou-Hezhou Huai crossing"),
    (2143, 5063, 5042, "Haozhou-Chuzhou Huai crossing"),
    (2143, 2142, 1896, "Haozhou-Huai'an Hongze crossing"),
    (2142, 4196, 5043, "Huai'an-Haizhou Huai crossing"),
    (4196, 5020, 5044, "Haizhou-Yancheng estuary crossing"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def definition_colours() -> dict[int, tuple[int, int, int]]:
    result: dict[int, tuple[int, int, int]] = {}
    with (MAP / "definition.csv").open(encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                result[int(row[0])] = tuple(int(value) for value in row[1:4])
    return result


def colour_mask(values: np.ndarray, colour: tuple[int, int, int]) -> np.ndarray:
    return np.all(values == np.array(colour, dtype=np.uint8), axis=2)


def component_sizes(mask: np.ndarray) -> list[int]:
    seen = np.zeros(mask.shape, dtype=bool)
    sizes: list[int] = []
    height, width = mask.shape
    for start_y, start_x in zip(*np.where(mask)):
        if seen[start_y, start_x]:
            continue
        queue = deque([(int(start_y), int(start_x))])
        seen[start_y, start_x] = True
        size = 0
        while queue:
            y, x = queue.popleft()
            size += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        sizes.append(size)
    return sorted(sizes, reverse=True)


def edge_contacts(ids: np.ndarray, province_id: int, water_id: int) -> int:
    province = ids == province_id
    water = ids == water_id
    return int(
        np.count_nonzero(province[:-1, :] & water[1:, :])
        + np.count_nonzero(province[1:, :] & water[:-1, :])
        + np.count_nonzero(province[:, :-1] & water[:, 1:])
        + np.count_nonzero(province[:, 1:] & water[:, :-1])
    )


def decode_ids(values: np.ndarray, colours: dict[int, tuple[int, int, int]]) -> np.ndarray:
    codes = (
        values[:, :, 0].astype(np.int32) << 16
        | values[:, :, 1].astype(np.int32) << 8
        | values[:, :, 2].astype(np.int32)
    )
    ids = np.full(codes.shape, -1, dtype=np.int32)
    for province_id, (red, green, blue) in colours.items():
        ids[codes == ((red << 16) | (green << 8) | blue)] = province_id
    return ids


def guarded_set(pixel: np.ndarray, source: tuple[int, int, int], target: tuple[int, int, int], label: str) -> int:
    current = tuple(int(value) for value in pixel)
    if current not in {source, target}:
        raise ValueError(f"{label}: unexpected RGB {current}; expected {source} or {target}")
    if current == target:
        return 0
    pixel[:] = np.array(target, dtype=np.uint8)
    return 1


def repair_pixels(colours: dict[int, tuple[int, int, int]]) -> tuple[int, set[tuple[int, int]]]:
    with Image.open(PROVINCES) as source:
        values = np.array(source.convert("RGB"), dtype=np.uint8, copy=True)

    changed = 0
    changed_points: set[tuple[int, int]] = set()
    source_colour = colours[2142]
    target_colour = colours[5018]
    for y, start_x, end_x in HUAIAN_TO_SUQIAN:
        for x in range(start_x, end_x + 1):
            delta = guarded_set(values[y, x], source_colour, target_colour, f"Huai'an run {x},{y}")
            changed += delta
            if delta:
                changed_points.add((x, y))

    for x, y, source_id, target_id in PIXEL_REASSIGNMENTS:
        delta = guarded_set(values[y, x], colours[source_id], colours[target_id], f"pixel {x},{y}")
        changed += delta
        if delta:
            changed_points.add((x, y))

    Image.fromarray(values, mode="RGB").save(PROVINCES, format="BMP")

    # Only two reviewed crumbs become navigable water.
    water_points = {(4650, 842): 1896, (4628, 846): 5041}
    with Image.open(HEIGHTMAP) as source:
        heights = np.array(source.convert("L"), dtype=np.uint8, copy=True)
    with Image.open(RIVERS) as source:
        palette = source.getpalette()
        rivers = np.array(source, dtype=np.uint8, copy=True)
    for (x, y), water_id in water_points.items():
        heights[y, x] = 92 if water_id == 1896 else 93
        rivers[y, x] = 254
    Image.fromarray(heights, mode="L").save(HEIGHTMAP, format="BMP")
    river_image = Image.fromarray(rivers, mode="P")
    river_image.putpalette(palette)
    river_image.save(RIVERS, format="BMP")
    return changed, changed_points


def rebuild_crossings() -> tuple[int, int]:
    with ADJACENCIES.open(encoding="cp1252", errors="strict", newline="") as handle:
        rows = list(csv.reader(handle, delimiter=";"))

    kept: list[list[str]] = []
    removed = 0
    insert_at: int | None = None
    for row in rows:
        if len(row) > 3 and row[0].isdigit() and row[3].isdigit() and int(row[3]) in HUAI_WATERS:
            if insert_at is None:
                insert_at = len(kept)
            removed += 1
            continue
        kept.append(row)

    new_rows = [
        [str(start), str(end), "sea", str(through), "-1", "-1", "-1", "-1", comment]
        for start, end, through, comment in CROSSINGS
    ]
    # Keep the existing Jingzhou-Gongan row after the Huai block so this
    # focused transaction does not create an unrelated ordering diff.
    jingzhou_index = next(
        (
            index
            for index, row in enumerate(kept)
            if len(row) > 3 and {row[0], row[1]} == {"2172", "5014"} and row[3] == "5036"
        ),
        None,
    )
    if jingzhou_index is not None:
        insert_at = jingzhou_index
    if insert_at is None:
        insert_at = next((index for index, row in enumerate(kept) if row and row[0] == "-1"), len(kept))
    kept[insert_at:insert_at] = new_rows
    with ADJACENCIES.open("w", encoding="cp1252", newline="") as handle:
        writer = csv.writer(handle, delimiter=";", lineterminator="\n")
        writer.writerows(kept)
    return removed, len(new_rows)


def validate(colours: dict[int, tuple[int, int, int]]) -> dict[str, object]:
    values = np.asarray(Image.open(PROVINCES).convert("RGB"), dtype=np.uint8)
    ids = decode_ids(values, colours)
    checked_land = (2142, 2143, 4196, 5018, 5020, 5117)
    connectivity = {
        str(province_id): component_sizes(colour_mask(values, colours[province_id]))
        for province_id in checked_land
    }
    fragmented = {province_id: sizes for province_id, sizes in connectivity.items() if len(sizes) != 1}
    if fragmented:
        raise ValueError(f"B75 left fragmented provinces: {fragmented}")

    contacts = {}
    for start, end, through, _comment in CROSSINGS:
        pair = (edge_contacts(ids, start, through), edge_contacts(ids, end, through))
        contacts[f"{start}-{end}-via-{through}"] = pair
        if min(pair) <= 0:
            raise ValueError(f"Crossing {start}-{end} does not touch through province {through}: {pair}")

    text = ADJACENCIES.read_text(encoding="cp1252")
    stale_pairs = ("5055;2175;sea;5039;", "5053;2175;sea;5039;", "5054;2175;sea;5040;", "5054;2144;sea;5040;", "2175;2144;sea;5040;", "2144;5059;sea;5041;")
    remaining = [row for row in stale_pairs if row in text]
    if remaining:
        raise ValueError(f"Stale Huai crossings remain: {remaining}")
    return {"province_component_sizes": connectivity, "crossing_water_contacts": contacts}


def render_preview(colours: dict[int, tuple[int, int, int]]) -> None:
    with Image.open(PROVINCES) as source:
        crop = source.convert("RGB").crop((4540, 805, 4690, 880))
    crop = crop.resize((900, 450), Image.Resampling.NEAREST)
    crop.save(PREVIEW)


def apply() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    colours = definition_colours()
    changed, changed_points = repair_pixels(colours)
    removed, added = rebuild_crossings()
    validation = validate(colours)
    render_preview(colours)
    canonical_hashes = {path.name: sha256(path) for path in (PROVINCES, HEIGHTMAP, RIVERS, ADJACENCIES)}
    reviewed_points = {
        (x, y)
        for y, start_x, end_x in HUAIAN_TO_SUQIAN
        for x in range(start_x, end_x + 1)
    } | {(x, y) for x, y, _source_id, _target_id in PIXEL_REASSIGNMENTS}
    REPORT.write_text(
        json.dumps(
            {
                "batch": MARKER,
                "purpose": "Repair stale Huai crossings and fragmented river-bank provinces after B47.",
                "reviewed_reassigned_pixels": len(reviewed_points),
                "reviewed_pixel_coordinates": sorted(reviewed_points),
                "exterior_changed_pixels": 0,
                "canonical_huai_crossings": added,
                "crossings": CROSSINGS,
                "validation": validation,
                "canonical_hashes": canonical_hashes,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{MARKER}; CHANGED_PIXELS:{changed}; CROSSINGS:{removed}->{added}; PASS")


if __name__ == "__main__":
    apply()
