#!/usr/bin/env python3
"""Apply a blended East/Southeast Asia terrain transplant from workshop 1728520255."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import render_adapted_workshop_han_mountains_draft as adapted


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
SOURCE = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
OUT = ROOT / "planning/terrain_transplant/daming_han_v1"
BACKUP = OUT / "pre_b38/map/terrain.bmp"
PLATEAU_BACKUP = OUT / "pre_b40_white_tibet/map/terrain.bmp"
SOURCE_OFFSET = (438, 9)
LEGACY_WINDOW = (4300, 680, 4730, 1060)
TRANSITION_RADIUS = 120
NOISE_SCALE = 18
NOISE_SEED = 1728520255
LOCKED_TERRAIN_INDICES = (15, 17, 35)  # ocean, inland ocean, coastline
PLATEAU_MOUNTAIN_INDICES = (1, 2, 6, 7, 8, 16, 23, 24)
PLATEAU_CLOSE_RADIUS = 6
PLATEAU_MIN_HEIGHT = 80
PLATEAU_FILL_INDEX = 6

CORE_REGIONS = (
    "mongolia_region", "manchuria_region", "korea_region", "japan_region",
    "tibet_region", "north_china_region", "south_china_region", "xinan_region",
    "burma_region", "indo_china_region", "malaya_region", "moluccas_region",
    "indonesia_region",
)

INDEX_CATEGORY = {
    0: "grasslands", 1: "hills", 2: "mountain", 3: "desert",
    4: "grasslands", 5: "grasslands", 6: "mountain", 7: "desert",
    8: "hills", 9: "marsh", 10: "farmlands", 11: "farmlands",
    12: "forest", 13: "forest", 14: "forest", 15: "ocean",
    16: "mountain", 17: "inland_ocean", 19: "coastal_desert",
    20: "savannah", 21: "farmlands", 22: "drylands", 23: "highlands",
    24: "highlands", 35: "coastline", 254: "jungle", 255: "woods",
}
_CATEGORY_NAMES = sorted({INDEX_CATEGORY.get(index, f"index_{index}") for index in range(256)})
_CATEGORY_NUMBERS = {name: number for number, name in enumerate(_CATEGORY_NAMES)}
CATEGORY_CODE = np.array([
    _CATEGORY_NUMBERS[INDEX_CATEGORY.get(index, f"index_{index}")]
    for index in range(256)
], dtype=np.int16)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def definitions(path: Path) -> dict[int, tuple[int, int, int]]:
    result = {}
    with path.open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                result[int(row[0])] = tuple(map(int, row[1:4]))
    return result


def packed_rgb(values: np.ndarray) -> np.ndarray:
    return (
        (values[:, :, 0].astype(np.uint32) << 16)
        | (values[:, :, 1].astype(np.uint32) << 8)
        | values[:, :, 2].astype(np.uint32)
    )


def named_blocks(text: str, suffix: str) -> dict[str, str]:
    result = {}
    pattern = re.compile(rf"(?m)^\s*([A-Za-z0-9_]+{re.escape(suffix)})\s*=\s*\{{")
    for match in pattern.finditer(text):
        depth = 1
        index = match.end()
        while index < len(text) and depth:
            depth += (text[index] == "{") - (text[index] == "}")
            index += 1
        if depth:
            raise ValueError(f"Unclosed block: {match.group(1)}")
        result[match.group(1)] = text[match.end():index - 1]
    return result


def area_ids(body: str) -> list[int]:
    clean = re.sub(r"#.*", "", body)
    clean = re.sub(r"(?ms)\bcolor\s*=\s*\{.*?\}", "", clean)
    return list(map(int, re.findall(r"\b\d+\b", clean)))


def terrain_overrides(path: Path) -> set[int]:
    text = re.sub(r"#.*", "", path.read_text(encoding="cp1252", errors="replace"))
    result: set[int] = set()
    position = 0
    while True:
        match = re.search(r"\bterrain_override\s*=\s*\{", text[position:])
        if not match:
            return result
        start = position + match.end()
        depth = 1
        index = start
        while index < len(text) and depth:
            depth += (text[index] == "{") - (text[index] == "}")
            index += 1
        if depth:
            raise ValueError("Unclosed terrain_override block")
        result.update(map(int, re.findall(r"\b\d+\b", text[start:index - 1])))
        position = index


def modal_indices(
    province_pixels: np.ndarray,
    terrain: np.ndarray,
    packed_to_id: dict[int, int],
) -> dict[int, int]:
    joint = (province_pixels.astype(np.uint64) << 8) | terrain.astype(np.uint64)
    keys, counts = np.unique(joint, return_counts=True)
    best: dict[int, tuple[int, int]] = {}
    for key, count in zip(keys.tolist(), counts.tolist()):
        province_id = packed_to_id.get(key >> 8)
        if province_id is None:
            continue
        terrain_index = key & 255
        if province_id not in best or count > best[province_id][1]:
            best[province_id] = (terrain_index, count)
    return {province_id: value[0] for province_id, value in best.items()}


def region_ids(regions: tuple[str, ...]) -> set[int]:
    region_blocks = named_blocks(
        (MAP / "region.txt").read_text(encoding="cp1252", errors="replace"),
        "_region",
    )
    area_blocks = named_blocks(
        (MAP / "area.txt").read_text(encoding="cp1252", errors="replace"),
        "_area",
    )
    area_keys = {
        key
        for region in regions
        for key in re.findall(r"\b[A-Za-z0-9_]+_area\b", re.sub(r"#.*", "", region_blocks.get(region, "")))
    }
    missing = sorted(area_keys - area_blocks.keys())
    if missing:
        raise ValueError(f"Core regions reference missing areas: {missing}")
    return {province_id for key in area_keys for province_id in area_ids(area_blocks[key])}


def region_core_ids() -> set[int]:
    return region_ids(CORE_REGIONS)


def plateau_continuity(
    terrain: np.ndarray,
    reference_terrain: np.ndarray,
    province_pixels: np.ndarray,
    defs: dict[int, tuple[int, int, int]],
) -> tuple[np.ndarray, np.ndarray]:
    plateau_ids = region_ids(("tibet_region",))
    plateau_values = np.array([
        (defs[province_id][0] << 16) | (defs[province_id][1] << 8) | defs[province_id][2]
        for province_id in plateau_ids if province_id in defs
    ], dtype=np.uint32)
    plateau = np.isin(province_pixels, plateau_values)
    ys, xs = np.where(plateau)
    if not len(xs):
        raise ValueError("Qinghai-Tibet plateau mask is empty")
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    local_plateau = plateau[y0:y1, x0:x1]
    local_terrain = terrain[y0:y1, x0:x1]
    local_reference = reference_terrain[y0:y1, x0:x1]
    local_height = np.asarray(Image.open(MAP / "heightmap.bmp"))[y0:y1, x0:x1]
    family = np.isin(local_reference, PLATEAU_MOUNTAIN_INDICES) & local_plateau
    family_image = Image.fromarray(family.astype(np.uint8) * 255, mode="L")
    size = PLATEAU_CLOSE_RADIUS * 2 + 1
    closed = np.asarray(
        family_image.filter(ImageFilter.MaxFilter(size)).filter(ImageFilter.MinFilter(size))
    ) > 0
    fill_local = (
        closed
        & local_plateau
        & (local_height >= PLATEAU_MIN_HEIGHT)
        & ~np.isin(local_reference, LOCKED_TERRAIN_INDICES)
        & ~family
    )
    result = terrain.copy()
    result[y0:y1, x0:x1][fill_local] = PLATEAU_FILL_INDEX
    fill = np.zeros(terrain.shape, dtype=bool)
    fill[y0:y1, x0:x1] = fill_local
    return result, fill


def coherent_transition(core: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    core_image = Image.fromarray((core.astype(np.uint8) * 255), mode="L")
    fade = np.asarray(core_image.filter(ImageFilter.GaussianBlur(TRANSITION_RADIUS)), dtype=np.float32) / 255.0
    fade[core] = 1.0
    height, width = core.shape
    rng = np.random.default_rng(NOISE_SEED)
    small = rng.integers(
        0, 256,
        size=(math.ceil(height / NOISE_SCALE), math.ceil(width / NOISE_SCALE)),
        dtype=np.uint8,
    )
    noise_image = Image.fromarray(small, mode="L").resize((width, height), Image.Resampling.BILINEAR)
    noise = np.asarray(noise_image, dtype=np.float32) / 255.0
    adoption = core | (noise < fade)
    return adoption, fade > 0


def build_transaction() -> dict[str, object]:
    canonical = MAP / "terrain.bmp"
    OUT.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(canonical, BACKUP)
    if not PLATEAU_BACKUP.exists():
        PLATEAU_BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(canonical, PLATEAU_BACKUP)

    current_image = Image.open(canonical)
    baseline_image = Image.open(BACKUP)
    source_image = Image.open(SOURCE / "map/terrain.bmp")
    if current_image.mode != "P" or baseline_image.mode != "P" or source_image.mode != "P":
        raise ValueError("terrain.bmp must remain an indexed 8-bit bitmap")
    if current_image.size != baseline_image.size:
        raise ValueError("Canonical and backup terrain dimensions differ")
    if current_image.getpalette() != baseline_image.getpalette() or baseline_image.getpalette() != source_image.getpalette():
        raise ValueError("Terrain palettes differ")

    current = np.asarray(current_image).copy()
    baseline = np.asarray(baseline_image)
    source_full = np.asarray(source_image)
    height, width = baseline.shape
    offset_x, offset_y = SOURCE_OFFSET
    source = source_full[offset_y:offset_y + height, offset_x:offset_x + width]
    if source.shape != baseline.shape:
        raise ValueError(f"Translated source terrain has shape {source.shape}, expected {baseline.shape}")

    province_image = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    province_pixels = packed_rgb(province_image)
    defs = definitions(MAP / "definition.csv")
    default_text = (MAP / "default.map").read_text(encoding="cp1252", errors="replace")
    climate_text = (MAP / "climate.txt").read_text(encoding="cp1252", errors="replace")
    water_ids = adapted.numeric_block(default_text, "sea_starts") | adapted.numeric_block(default_text, "lakes")
    impassable_ids = adapted.numeric_block(climate_text, "impassable")
    water_values = np.array([
        (defs[province_id][0] << 16) | (defs[province_id][1] << 8) | defs[province_id][2]
        for province_id in water_ids if province_id in defs
    ], dtype=np.uint32)
    province_water = np.isin(province_pixels, water_values)

    core_ids = region_core_ids() - water_ids
    core_values = np.array([
        (defs[province_id][0] << 16) | (defs[province_id][1] << 8) | defs[province_id][2]
        for province_id in core_ids if province_id in defs
    ], dtype=np.uint32)
    core = np.isin(province_pixels, core_values) & ~province_water
    adoption, transition_extent = coherent_transition(core)

    overrides = terrain_overrides(MAP / "terrain.txt")
    override_values = np.array([
        (defs[province_id][0] << 16) | (defs[province_id][1] << 8) | defs[province_id][2]
        for province_id in overrides if province_id in defs
    ], dtype=np.uint32)
    override_pixels = np.isin(province_pixels, override_values)
    same_category = CATEGORY_CODE[baseline] == CATEGORY_CODE[source]
    safe_land = (
        ~province_water
        & ~np.isin(baseline, LOCKED_TERRAIN_INDICES)
        & ~np.isin(source, LOCKED_TERRAIN_INDICES)
    )
    editable = adoption & safe_land & (override_pixels | same_category)

    draft = baseline.copy()
    draft[editable] = source[editable]
    result = current.copy()
    legacy = np.zeros(baseline.shape, dtype=bool)
    lx0, ly0, lx1, ly1 = LEGACY_WINDOW
    legacy[ly0:ly1, lx0:lx1] = True
    result[legacy] = baseline[legacy]
    result[editable] = draft[editable]
    plateau_reference = np.asarray(Image.open(PLATEAU_BACKUP))
    result, plateau_fill = plateau_continuity(
        result, plateau_reference, province_pixels, defs
    )
    owned = editable | legacy | plateau_fill
    changed_this_run = current != result
    if (changed_this_run & ~owned).any():
        raise ValueError("Terrain transaction changed pixels outside its owned mask")

    affected_colours = np.unique(province_image[transition_extent].reshape(-1, 3), axis=0)
    by_colour = {colour: province_id for province_id, colour in defs.items()}
    protected = water_ids | impassable_ids
    affected_ids = {
        by_colour[tuple(map(int, colour))]
        for colour in affected_colours
        if tuple(map(int, colour)) in by_colour and by_colour[tuple(map(int, colour))] not in protected
    }
    packed_to_id = {
        (colour[0] << 16) | (colour[1] << 8) | colour[2]: province_id
        for province_id, colour in defs.items() if province_id in affected_ids
    }
    before_modes = modal_indices(province_pixels, baseline, packed_to_id)
    after_modes = modal_indices(province_pixels, result, packed_to_id)
    unprotected_changes = [
        province_id for province_id in sorted(affected_ids)
        if province_id not in overrides
        and INDEX_CATEGORY.get(before_modes[province_id], str(before_modes[province_id]))
        != INDEX_CATEGORY.get(after_modes[province_id], str(after_modes[province_id]))
    ]
    if unprotected_changes:
        raise ValueError(f"Unprotected gameplay terrain changes remain: {unprotected_changes}")

    return {
        "current_image": current_image,
        "current": current,
        "baseline": baseline,
        "source": source,
        "result": result,
        "core": core,
        "transition_extent": transition_extent,
        "editable": editable,
        "owned": owned,
        "affected_ids": affected_ids,
        "unprotected_changes": unprotected_changes,
        "blocked_cross_category_pixels": int((adoption & safe_land & ~override_pixels & ~same_category).sum()),
        "plateau_fill": plateau_fill,
    }


def mask_bbox(mask: np.ndarray, margin: int = 20) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    if not len(xs):
        raise ValueError("Transition mask is empty")
    return (
        max(0, int(xs.min()) - margin), max(0, int(ys.min()) - margin),
        min(mask.shape[1], int(xs.max()) + margin + 1), min(mask.shape[0], int(ys.max()) + margin + 1),
    )


def write_preview(
    baseline: np.ndarray,
    source: np.ndarray,
    result: np.ndarray,
    transition_extent: np.ndarray,
    palette: list[int],
) -> tuple[Path, tuple[int, int, int, int]]:
    crop_box = mask_bbox(transition_extent)
    x0, y0, x1, y1 = crop_box

    def panel(values: np.ndarray) -> Image.Image:
        image = Image.fromarray(values[y0:y1, x0:x1].astype(np.uint8), mode="P")
        image.putpalette(palette)
        return image.convert("RGB")

    panels = (panel(baseline), panel(source), panel(result))
    titles = ("实装前", "大明日不落源图", "东亚—东南亚渐变移植")
    top = 48
    canvas = Image.new("RGB", (panels[0].width * 3, panels[0].height + top), (244, 242, 236))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 23)
    for index, (image, title) in enumerate(zip(panels, titles)):
        x = index * image.width
        canvas.paste(image, (x, top))
        draw.text((x + 18, 8), title, font=font, fill=(25, 25, 25))
    path = OUT / "daming_han_terrain_formal_preview.png"
    canvas.save(path)
    return path, crop_box


def write_plateau_preview(
    before: np.ndarray,
    result: np.ndarray,
    fill: np.ndarray,
    palette: list[int],
) -> Path:
    x0, y0, x1, y1 = mask_bbox(fill, margin=60)
    panels = []
    for values in (before, result):
        image = Image.fromarray(values[y0:y1, x0:x1].astype(np.uint8), mode="P")
        image.putpalette(palette)
        panels.append(image.convert("RGB").resize(
            ((x1 - x0) * 3, (y1 - y0) * 3), Image.Resampling.NEAREST
        ))
    titles = ("青藏连续化前", "青藏山地闭合后")
    top = 48
    canvas = Image.new("RGB", (panels[0].width * 2, panels[0].height + top), (244, 242, 236))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 23)
    for index, (image, title) in enumerate(zip(panels, titles)):
        x = index * image.width
        canvas.paste(image, (x, top))
        draw.text((x + 18, 8), title, font=font, fill=(25, 25, 25))
    path = OUT / "tibet_terrain_continuity_preview.png"
    canvas.save(path)
    return path


def main() -> None:
    canonical = MAP / "terrain.bmp"
    tx = build_transaction()
    current_image = tx["current_image"]
    baseline = tx["baseline"]
    result = tx["result"]
    palette = current_image.getpalette()
    output = Image.fromarray(result.astype(np.uint8), mode="P")
    output.putpalette(palette)
    output.save(canonical, format="BMP")

    exterior = (tx["current"] != result) & ~tx["owned"]
    if exterior.any():
        raise ValueError("Formal terrain differs outside the approved owned mask")
    locked = np.isin(baseline, LOCKED_TERRAIN_INDICES)
    if not np.array_equal(baseline[locked], result[locked]):
        raise ValueError("Current water or coastline terrain pixels changed")
    formal = Image.open(canonical)
    if formal.mode != "P" or formal.size != current_image.size or formal.getpalette() != palette:
        raise ValueError("Formal terrain bitmap format or palette changed")

    preview, crop_box = write_preview(
        baseline, tx["source"], result, tx["transition_extent"], palette
    )
    plateau_before = np.asarray(Image.open(PLATEAU_BACKUP))
    plateau_preview = write_plateau_preview(
        plateau_before, result, tx["plateau_fill"], palette
    )
    report = {
        "batch": "B38 Daming East and Southeast Asia blended terrain transplant",
        "source": str(SOURCE / "map/terrain.bmp"),
        "source_offset": list(SOURCE_OFFSET),
        "core_regions": list(CORE_REGIONS),
        "transition_radius": TRANSITION_RADIUS,
        "transition_noise_scale": NOISE_SCALE,
        "plateau_close_radius": PLATEAU_CLOSE_RADIUS,
        "plateau_min_height": PLATEAU_MIN_HEIGHT,
        "plateau_fill_index": PLATEAU_FILL_INDEX,
        "plateau_fill_pixels": int(tx["plateau_fill"].sum()),
        "preview_crop": list(crop_box),
        "core_land_pixels": int(tx["core"].sum()),
        "transition_extent_pixels": int(tx["transition_extent"].sum()),
        "editable_pixels": int(tx["editable"].sum()),
        "formal_changed_pixels": int((baseline != result).sum()),
        "exterior_changed_pixels": int(exterior.sum()),
        "affected_playable_provinces": len(tx["affected_ids"]),
        "blocked_cross_category_pixels": tx["blocked_cross_category_pixels"],
        "unprotected_modal_category_changes": len(tx["unprotected_changes"]),
        "canonical_sha256": sha256(canonical),
        "backup_sha256": sha256(BACKUP),
        "heightmap_sha256": sha256(MAP / "heightmap.bmp"),
        "rivers_sha256": sha256(MAP / "rivers.bmp"),
        "preview": str(preview),
        "plateau_preview": str(plateau_preview),
        "backup": str(BACKUP),
        "plateau_backup": str(PLATEAU_BACKUP),
    }
    report_path = OUT / "daming_han_terrain_apply_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"B38_TERRAIN_APPLIED; PIXELS:{report['formal_changed_pixels']}; "
        f"AFFECTED:{report['affected_playable_provinces']}; "
        f"EXTERIOR:{report['exterior_changed_pixels']}"
    )
    print(report_path)
    print(preview)


if __name__ == "__main__":
    main()
