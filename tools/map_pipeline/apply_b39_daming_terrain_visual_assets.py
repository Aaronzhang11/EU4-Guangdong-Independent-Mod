#!/usr/bin/env python3
"""Adapt Daming terrain rendering assets to the current map transactionally."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import struct
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
SOURCE = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
VANILLA = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "common/Europa Universalis IV"
)
OUT = ROOT / "planning/terrain_transplant/daming_visual_assets_v1"
BACKUP = OUT / "pre_b39"
WHITE_FIX_BACKUP = OUT / "pre_b40_white_fix/map/terrain"
TREE_FIX_BACKUP = OUT / "pre_b41_tree_fix/map/trees.bmp"
TARGET_SIZE = (5632, 2048)
SOURCE_OFFSET = (438, 9)
TRANSITION_RADIUS = 180
SOURCE_BLANK_THRESHOLD = 220
SOURCE_BLANK_EXPAND = 9
SOURCE_BLANK_FEATHER = 4
TREE_TARGET_SIZE = (704, 293)
TREE_VALID_INDICES = (0, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 18, 19, 20, 27, 28, 29, 30)
TREE_INDEX_REMAP = {16: 13}
TREE_WATER_FRACTION_LIMIT = 0.05

CORE_REGIONS = (
    "mongolia_region", "manchuria_region", "korea_region", "japan_region",
    "tibet_region", "north_china_region", "south_china_region", "xinan_region",
    "burma_region", "indo_china_region", "malaya_region", "moluccas_region",
    "indonesia_region",
)

SEASONAL = (
    "colormap_spring.dds", "colormap_summer.dds",
    "colormap_autumn.dds", "colormap_winter.dds",
)

COPIED_TERRAIN_ASSETS = (
    "atlas0.dds", "atlas_normal0.dds",
    "RiverSurface_diffuse.dds", "RiverSurface_normal.dds", "River_normal.bmp",
    "Tree_tint.bmp", "Tree_season.bmp",
    "colormap_water.dds", "underwater_terrain.dds", "ice_normal.dds",
    "reflection.dds", "map_overlay_tile.dds",
    "border0.dds", "border1.dds", "border5.dds", "border5data.dds", "border6.dds",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def definitions(path: Path) -> dict[int, tuple[int, int, int]]:
    result: dict[int, tuple[int, int, int]] = {}
    with path.open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                result[int(row[0])] = tuple(map(int, row[1:4]))
    return result


def named_blocks(text: str, suffix: str) -> dict[str, str]:
    result: dict[str, str] = {}
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


def numeric_block(text: str, key: str) -> set[int]:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"Missing numeric block: {key}")
    depth = 1
    index = match.end()
    while index < len(text) and depth:
        depth += (text[index] == "{") - (text[index] == "}")
        index += 1
    if depth:
        raise ValueError(f"Unclosed numeric block: {key}")
    body = re.sub(r"#.*", "", text[match.end():index - 1])
    return set(map(int, re.findall(r"\b\d+\b", body)))


def region_core_ids() -> set[int]:
    region_blocks = named_blocks(
        (MAP / "region.txt").read_text(encoding="cp1252", errors="replace"),
        "_region",
    )
    area_blocks = named_blocks(
        (MAP / "area.txt").read_text(encoding="cp1252", errors="replace"),
        "_area",
    )
    missing_regions = sorted(set(CORE_REGIONS) - region_blocks.keys())
    if missing_regions:
        raise ValueError(f"Missing core regions: {missing_regions}")
    area_keys = {
        key
        for region in CORE_REGIONS
        for key in re.findall(
            r"\b[A-Za-z0-9_]+_area\b",
            re.sub(r"#.*", "", region_blocks[region]),
        )
    }
    missing_areas = sorted(area_keys - area_blocks.keys())
    if missing_areas:
        raise ValueError(f"Core regions reference missing areas: {missing_areas}")
    return {province_id for key in area_keys for province_id in area_ids(area_blocks[key])}


def packed_rgb(values: np.ndarray) -> np.ndarray:
    return (
        (values[:, :, 0].astype(np.uint32) << 16)
        | (values[:, :, 1].astype(np.uint32) << 8)
        | values[:, :, 2].astype(np.uint32)
    )


def core_fade_and_water() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    province_image = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    if (province_image.shape[1], province_image.shape[0]) != TARGET_SIZE:
        raise ValueError(f"Unexpected target map dimensions: {province_image.shape}")
    defs = definitions(MAP / "definition.csv")
    default_text = (MAP / "default.map").read_text(encoding="cp1252", errors="replace")
    water_ids = numeric_block(default_text, "sea_starts") | numeric_block(default_text, "lakes")
    water_values = np.array([
        (defs[province_id][0] << 16) | (defs[province_id][1] << 8) | defs[province_id][2]
        for province_id in water_ids if province_id in defs
    ], dtype=np.uint32)
    province_pixels = packed_rgb(province_image)
    water = np.isin(province_pixels, water_values)
    values = np.array([
        (defs[province_id][0] << 16) | (defs[province_id][1] << 8) | defs[province_id][2]
        for province_id in region_core_ids() - water_ids if province_id in defs
    ], dtype=np.uint32)
    core = np.isin(province_pixels, values) & ~water
    core_image = Image.fromarray(core.astype(np.uint8) * 255, mode="L")
    fade = np.asarray(
        core_image.filter(ImageFilter.GaussianBlur(TRANSITION_RADIUS)),
        dtype=np.float32,
    ) / 255.0
    fade[core] = 1.0
    return core, fade, water


def dds_payload(image: Image.Image, pixel_format: str = "DXT3") -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".dds") as handle:
        image.save(handle.name, pixel_format=pixel_format)
        data = Path(handle.name).read_bytes()
    if data[:4] != b"DDS " or len(data) < 128:
        raise ValueError("Pillow did not produce a classic DDS file")
    return data[128:]


def save_dxt3_with_mips(image: Image.Image, path: Path) -> None:
    image = image.convert("RGBA")
    levels: list[Image.Image] = [image]
    while levels[-1].size != (1, 1):
        width, height = levels[-1].size
        levels.append(levels[-1].resize(
            (max(1, width // 2), max(1, height // 2)),
            Image.Resampling.LANCZOS,
        ))
    with tempfile.NamedTemporaryFile(suffix=".dds") as handle:
        levels[0].save(handle.name, pixel_format="DXT3")
        header = bytearray(Path(handle.name).read_bytes()[:128])
    flags = struct.unpack_from("<I", header, 8)[0] | 0x00020000
    struct.pack_into("<I", header, 8, flags)
    width, height = image.size
    linear_size = ((width + 3) // 4) * ((height + 3) // 4) * 16
    struct.pack_into("<I", header, 20, linear_size)
    struct.pack_into("<I", header, 28, len(levels))
    caps = struct.unpack_from("<I", header, 108)[0] | 0x00000008 | 0x00400000
    struct.pack_into("<I", header, 108, caps)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(header) + b"".join(dds_payload(level) for level in levels))


def blend_seasonal(
    name: str,
    fade: np.ndarray,
    water: np.ndarray,
) -> tuple[Image.Image, dict[str, int]]:
    source_path = SOURCE / "map/terrain" / name
    vanilla_path = VANILLA / "map/terrain" / name
    source_full = Image.open(source_path).convert("RGBA")
    if source_full.size != (6400, 2560):
        raise ValueError(f"Unexpected source size for {name}: {source_full.size}")
    x0, y0 = SOURCE_OFFSET
    source = source_full.crop((x0, y0, x0 + TARGET_SIZE[0], y0 + TARGET_SIZE[1]))
    baseline = Image.open(vanilla_path).convert("RGBA").resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    source_values = np.asarray(source)
    near_white = np.all(source_values[:, :, :3] >= SOURCE_BLANK_THRESHOLD, axis=2)
    expanded = Image.fromarray(near_white.astype(np.uint8) * 255, mode="L").filter(
        ImageFilter.MaxFilter(SOURCE_BLANK_EXPAND)
    )
    invalid_soft = np.asarray(
        expanded.filter(ImageFilter.GaussianBlur(SOURCE_BLANK_FEATHER)), dtype=np.float32
    ) / 255.0
    effective = fade * (1.0 - invalid_soft)
    effective[near_white] = 0.0
    effective[water] = 0.0
    mask = Image.fromarray(np.clip(effective * 255.0, 0, 255).astype(np.uint8), mode="L")
    result = Image.composite(source, baseline, mask)
    # The engine can expose white RGB even when an authoring tool expected transparency.
    result.putalpha(255)
    result_values = np.asarray(result)
    stats = {
        "source_near_white_pixels": int(near_white.sum()),
        "near_white_adopted_pixels": int((near_white & (effective > 0)).sum()),
        "water_adopted_pixels": int((water & (effective > 0)).sum()),
        "result_near_white_pixels": int(np.all(
            result_values[:, :, :3] >= SOURCE_BLANK_THRESHOLD, axis=2
        ).sum()),
    }
    if stats["near_white_adopted_pixels"] or stats["water_adopted_pixels"]:
        raise ValueError(f"White/water exclusion failed for {name}: {stats}")
    return result, stats


def adapt_trees(
    core: np.ndarray,
    fade: np.ndarray,
    water: np.ndarray,
) -> tuple[Image.Image, dict[str, object]]:
    source_image = Image.open(SOURCE / "map/trees.bmp")
    vanilla_image = Image.open(VANILLA / "map/trees.bmp")
    if source_image.mode != "P" or vanilla_image.mode != "P":
        raise ValueError("trees.bmp inputs must remain indexed bitmaps")
    if source_image.getpalette() != vanilla_image.getpalette():
        raise ValueError("Source and vanilla tree palettes differ")
    if vanilla_image.size != TREE_TARGET_SIZE:
        raise ValueError(f"Unexpected vanilla trees.bmp size: {vanilla_image.size}")
    scale_x = source_image.width / 6400.0
    scale_y = source_image.height / 2560.0
    x0, y0 = SOURCE_OFFSET
    extent = (
        x0 * scale_x, y0 * scale_y,
        (x0 + TARGET_SIZE[0]) * scale_x,
        (y0 + TARGET_SIZE[1]) * scale_y,
    )
    source = source_image.transform(
        TREE_TARGET_SIZE, Image.Transform.EXTENT, extent, Image.Resampling.NEAREST
    )
    baseline = vanilla_image
    # Categorical tree indices use an organic dither in the transition instead of antialiasing.
    fade_small = np.asarray(
        Image.fromarray(np.clip(fade * 255.0, 0, 255).astype(np.uint8), mode="L").resize(
            TREE_TARGET_SIZE, Image.Resampling.BILINEAR
        ),
        dtype=np.uint8,
    )
    rng = np.random.default_rng(1728520255)
    select = rng.integers(
        0, 256, size=(TREE_TARGET_SIZE[1], TREE_TARGET_SIZE[0]), dtype=np.uint8
    ) < fade_small
    select[np.asarray(Image.fromarray(core.astype(np.uint8) * 255, mode="L").resize(
        TREE_TARGET_SIZE, Image.Resampling.NEAREST
    )) > 0] = True
    result = np.asarray(baseline).copy()
    source_values = np.asarray(source)
    result[select] = source_values[select]

    remapped: dict[str, int] = {}
    for old, new in TREE_INDEX_REMAP.items():
        count = int((result == old).sum())
        if count:
            result[result == old] = new
        remapped[f"{old}->{new}"] = count
    undefined = sorted(set(np.unique(result).tolist()) - set(TREE_VALID_INDICES))
    if undefined:
        raise ValueError(f"Undefined nonzero tree indices remain: {undefined}")

    water_fraction = np.asarray(
        Image.fromarray(water.astype(np.uint8) * 255, mode="L").resize(
            TREE_TARGET_SIZE, Image.Resampling.BOX
        ),
        dtype=np.float32,
    ) / 255.0
    water_cells = water_fraction > TREE_WATER_FRACTION_LIMIT
    water_trees_before = int(((result != 0) & water_cells).sum())
    result[water_cells] = 0
    water_trees_after = int(((result != 0) & water_cells).sum())
    if water_trees_after:
        raise ValueError(f"Trees remain on water cells: {water_trees_after}")

    output = Image.fromarray(result.astype(np.uint8), mode="P")
    output.putpalette(source_image.getpalette())
    stats: dict[str, object] = {
        "source_size": list(source_image.size),
        "vanilla_target_size": list(vanilla_image.size),
        "output_size": list(output.size),
        "valid_indices": list(TREE_VALID_INDICES),
        "used_indices": sorted(map(int, np.unique(result).tolist())),
        "remapped_indices": remapped,
        "water_fraction_limit": TREE_WATER_FRACTION_LIMIT,
        "water_tree_cells_removed": water_trees_before,
        "water_tree_cells_after": water_trees_after,
    }
    return output, stats


def backup_once(owned: list[Path]) -> dict[str, object]:
    BACKUP.mkdir(parents=True, exist_ok=True)
    manifest_path = BACKUP / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    records = []
    for target in owned:
        relative = target.relative_to(MOD)
        existed = target.exists()
        baseline = target if existed else VANILLA / relative
        if not baseline.exists():
            raise FileNotFoundError(f"No current or inherited baseline for {relative}")
        backup = BACKUP / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(baseline, backup)
        records.append({
            "path": str(relative),
            "target_existed": existed,
            "baseline": str(baseline),
            "baseline_sha256": sha256(baseline),
        })
    manifest = {"batch": "B39", "files": records}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def preview(before: Image.Image, source: Image.Image, after: Image.Image) -> Path:
    # East China crop where the farmland-detail difference is easy to inspect.
    box = (4250, 650, 5050, 1250)
    panels = [image.crop(box).convert("RGB") for image in (before, source, after)]
    titles = ("原版继承色图", "大明日不落源色图", "本模组渐变适配结果")
    top = 48
    canvas = Image.new("RGB", (panels[0].width * 3, panels[0].height + top), (244, 242, 236))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 22)
    for index, (panel, title) in enumerate(zip(panels, titles)):
        x = index * panel.width
        canvas.paste(panel, (x, top))
        draw.text((x + 16, 9), title, fill=(20, 20, 20), font=font)
    path = OUT / "daming_visual_assets_preview.png"
    canvas.save(path)
    return path


def atlas_preview() -> Path:
    vanilla = Image.open(VANILLA / "map/terrain/atlas0.dds").convert("RGB")
    source = Image.open(SOURCE / "map/terrain/atlas0.dds").convert("RGB")
    panels = [image.resize((768, 768), Image.Resampling.LANCZOS) for image in (vanilla, source)]
    titles = ("原版地形纹理图集", "实装的大明日不落纹理图集")
    top = 48
    canvas = Image.new("RGB", (1536, 768 + top), (244, 242, 236))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 22)
    for index, (panel, title) in enumerate(zip(panels, titles)):
        x = index * 768
        canvas.paste(panel, (x, top))
        draw.text((x + 16, 9), title, fill=(20, 20, 20), font=font)
    path = OUT / "daming_atlas_comparison.png"
    canvas.save(path)
    return path


def tree_fix_preview(
    before: Image.Image,
    after: Image.Image,
    base: Image.Image,
) -> Path:
    crop = (3700, 350, 5450, 1750)
    panel_size = (875, 700)
    panels: list[Image.Image] = []
    for tree_image in (before, after):
        values = np.asarray(tree_image.resize(TARGET_SIZE, Image.Resampling.NEAREST))
        values = values[crop[1]:crop[3], crop[0]:crop[2]]
        tree_mask = Image.fromarray((values != 0).astype(np.uint8) * 255, mode="L").resize(
            panel_size, Image.Resampling.NEAREST
        )
        invalid_mask = Image.fromarray((values == 16).astype(np.uint8) * 255, mode="L").resize(
            panel_size, Image.Resampling.NEAREST
        )
        panel = base.crop(crop).convert("RGB").resize(panel_size, Image.Resampling.LANCZOS).convert("RGBA")
        green = Image.new("RGBA", panel_size, (20, 130, 35, 145))
        red = Image.new("RGBA", panel_size, (230, 25, 25, 220))
        panel = Image.composite(green, panel, tree_mask)
        panel = Image.composite(red, panel, invalid_mask)
        panels.append(panel.convert("RGB"))
    titles = ("修复前：880×320，红色为无效索引16", "修复后：704×293，海域已清空")
    top = 48
    canvas = Image.new("RGB", (panel_size[0] * 2, panel_size[1] + top), (244, 242, 236))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 22)
    for index, (panel, title) in enumerate(zip(panels, titles)):
        x = index * panel_size[0]
        canvas.paste(panel, (x, top))
        draw.text((x + 16, 9), title, fill=(20, 20, 20), font=font)
    path = OUT / "trees_fix_preview.png"
    canvas.save(path)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    target_terrain = MAP / "terrain"
    owned = [target_terrain / name for name in (*SEASONAL, *COPIED_TERRAIN_ASSETS)]
    owned.append(MAP / "trees.bmp")
    manifest = backup_once(owned)
    WHITE_FIX_BACKUP.mkdir(parents=True, exist_ok=True)
    for name in SEASONAL:
        current = target_terrain / name
        backup = WHITE_FIX_BACKUP / name
        if current.exists() and not backup.exists():
            shutil.copy2(current, backup)
    if (MAP / "trees.bmp").exists() and not TREE_FIX_BACKUP.exists():
        TREE_FIX_BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MAP / "trees.bmp", TREE_FIX_BACKUP)

    locked_paths = [
        MAP / "provinces.bmp", MAP / "terrain.bmp", MAP / "heightmap.bmp",
        MAP / "rivers.bmp", MAP / "terrain.txt",
    ]
    locked_before = {str(path): sha256(path) for path in locked_paths}
    core, fade, water = core_fade_and_water()

    seasonal_images: dict[str, Image.Image] = {}
    seasonal_stats: dict[str, dict[str, int]] = {}
    for name in SEASONAL:
        blended, stats = blend_seasonal(name, fade, water)
        target = target_terrain / name
        save_dxt3_with_mips(blended, target)
        decoded = np.asarray(Image.open(target).convert("RGBA"))
        decoded_near_white = np.all(
            decoded[:, :, :3] >= SOURCE_BLANK_THRESHOLD, axis=2
        )
        stats["decoded_near_white_pixels"] = int(decoded_near_white.sum())
        stats["decoded_near_white_water_pixels"] = int((decoded_near_white & water).sum())
        stats["decoded_nonopaque_pixels"] = int((decoded[:, :, 3] != 255).sum())
        if stats["decoded_near_white_water_pixels"] or stats["decoded_nonopaque_pixels"]:
            raise ValueError(f"Compressed DDS white/alpha validation failed for {name}: {stats}")
        seasonal_images[name] = blended
        seasonal_stats[name] = stats

    target_terrain.mkdir(parents=True, exist_ok=True)
    for name in COPIED_TERRAIN_ASSETS:
        source = SOURCE / "map/terrain" / name
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, target_terrain / name)

    trees, tree_stats = adapt_trees(core, fade, water)
    trees.save(MAP / "trees.bmp", format="BMP")

    locked_after = {str(path): sha256(path) for path in locked_paths}
    if locked_before != locked_after:
        raise ValueError("A locked gameplay/map bitmap changed during B39")

    before = Image.open(VANILLA / "map/terrain/colormap_summer.dds").convert("RGBA").resize(
        TARGET_SIZE, Image.Resampling.LANCZOS
    )
    source_full = Image.open(SOURCE / "map/terrain/colormap_summer.dds").convert("RGBA")
    x0, y0 = SOURCE_OFFSET
    source = source_full.crop((x0, y0, x0 + TARGET_SIZE[0], y0 + TARGET_SIZE[1]))
    preview_path = preview(before, source, seasonal_images["colormap_summer.dds"])
    atlas_preview_path = atlas_preview()
    tree_preview_path = tree_fix_preview(
        Image.open(TREE_FIX_BACKUP), trees, seasonal_images["colormap_summer.dds"]
    )

    outputs = owned + [preview_path, atlas_preview_path, tree_preview_path]
    report = {
        "batch": "B39 Daming terrain rendering asset adaptation",
        "source": str(SOURCE),
        "source_offset": list(SOURCE_OFFSET),
        "target_size": list(TARGET_SIZE),
        "core_regions": list(CORE_REGIONS),
        "transition_radius": TRANSITION_RADIUS,
        "source_blank_threshold": SOURCE_BLANK_THRESHOLD,
        "source_blank_expand": SOURCE_BLANK_EXPAND,
        "source_blank_feather": SOURCE_BLANK_FEATHER,
        "core_pixels": int(core.sum()),
        "transition_pixels": int(((fade > 0) & ~core).sum()),
        "water_pixels_locked": int(water.sum()),
        "seasonal_white_fix": seasonal_stats,
        "tree_fix": tree_stats,
        "locked_files": locked_after,
        "outputs": {str(path.relative_to(ROOT)): sha256(path) for path in outputs},
        "backup_manifest": str(BACKUP / "manifest.json"),
        "white_fix_backup": str(WHITE_FIX_BACKUP),
        "tree_fix_backup": str(TREE_FIX_BACKUP),
        "preview": str(preview_path),
        "atlas_preview": str(atlas_preview_path),
        "tree_preview": str(tree_preview_path),
        "preexisting_targets": [
            record["path"] for record in manifest["files"] if record["target_existed"]
        ],
    }
    report_path = OUT / "daming_visual_assets_apply_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"B39_VISUAL_ASSETS_APPLIED; CORE:{report['core_pixels']}; "
        f"TRANSITION:{report['transition_pixels']}; FILES:{len(owned)}"
    )
    print(report_path)
    print(preview_path)


if __name__ == "__main__":
    main()
