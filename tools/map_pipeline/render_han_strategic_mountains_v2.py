#!/usr/bin/env python3
"""Render a review-only strategic impassable-mountain plan for Han China.

The canonical provinces.bmp is never written.  Existing mountain provinces are
kept as anchors; new candidates use geometry adapted from the two authorised
workshop references, snapped to the current mod's land and province borders.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render_adapted_workshop_han_mountains_draft as adapted
import render_border_aligned_han_mountains_draft as border
import render_playability_han_mountains_draft as play
import render_workshop_han_impassable_draft as ming


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
OUT = ROOT / "planning/han_mountains/strategic_v2"
TWO_MILLENNIA = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/2935149060"
)
CROP = (4300, 675, 4740, 1080)
OFFSET_X = 438
OFFSET_Y = 9
MAX_PLAYABLE_COVERAGE = 0.36

# Deliberately omit secondary hills such as Tianmu, Xianxia, Jiuling and
# Dahongshan.  They remain ordinary mountain terrain so southern China is not
# divided into a maze of hard barriers.
GROUPS = {
    "燕赵晋秦": (
        "燕山西段", "燕山东段", "恒山", "太行山北段", "太行山南段",
        "吕梁山", "中条山", "伏牛山", "秦岭", "陇山",
    ),
    "江汉屏障": ("桐柏山", "大别山", "巫山", "大巴山"),
    "东南脊梁": ("武夷山", "罗霄山", "大庾岭", "九连山", "雪峰山", "越城岭", "十万大山"),
    "西南高地": ("大凉山", "哀牢山", "苗岭", "大娄山", "岷山"),
    "齐鲁山地": ("泰山",),
}

MING_IDS = {
    5147: "大凉山", 5152: "泰山", 5158: "武夷山", 5161: "罗霄山",
    5163: "大庾岭", 5164: "九连山", 5165: "雪峰山", 5167: "十万大山",
    5168: "哀牢山", 5169: "苗岭", 5170: "越城岭", 5171: "大娄山",
    5172: "巫山", 5173: "桐柏山", 5175: "大巴山", 5176: "岷山",
    5177: "恒山", 5178: "太行山北段", 5179: "太行山南段", 5180: "中条山",
    5181: "吕梁山", 5182: "伏牛山", 5183: "秦岭", 5187: "陇山",
    5237: "大别山",
}

# 风云世纪两千年 separates the Yanshan barrier into western and eastern
# provinces.  This is preferable to copying its whole dense mountain system.
TWO_MILLENNIA_IDS = {5238: "燕山西段", 5237: "燕山东段"}

GROUP_COLORS = {
    "燕赵晋秦": (63, 66, 73),
    "江汉屏障": (92, 94, 102),
    "东南脊梁": (124, 111, 96),
    "西南高地": (103, 91, 112),
    "齐鲁山地": (128, 128, 136),
}


def definitions(path: Path) -> dict[int, tuple[int, int, int]]:
    result = {}
    with path.open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                result[int(row[0])] = tuple(map(int, row[1:4]))
    return result


def largest_component(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    largest: list[tuple[int, int]] = []
    for sy, sx in zip(*np.where(mask), strict=True):
        if seen[sy, sx]:
            continue
        stack = [(int(sy), int(sx))]
        seen[sy, sx] = True
        component = []
        while stack:
            y, x = stack.pop()
            component.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(component) > len(largest):
            largest = component
    result = np.zeros(mask.shape, dtype=bool)
    for y, x in largest:
        result[y, x] = True
    return result


def current_impassable_mask(target: np.ndarray) -> np.ndarray:
    climate = (MOD / "map/climate.txt").read_text(encoding="cp1252", errors="replace")
    ids = adapted.numeric_block(climate, "impassable")
    defs = definitions(MOD / "map/definition.csv")
    colors = [defs[province_id] for province_id in ids if province_id in defs]
    return ming.mask_for(target, colors)


def load_two_millennia_masks(target_shape: tuple[int, ...], land: np.ndarray, borders: np.ndarray):
    source = np.asarray(Image.open(TWO_MILLENNIA / "map/provinces.bmp").convert("RGB"))
    translated = source[
        OFFSET_Y:OFFSET_Y + target_shape[0],
        OFFSET_X:OFFSET_X + target_shape[1],
    ]
    if translated.shape != target_shape:
        raise ValueError(f"Translated two-millennia map has shape {translated.shape}")
    defs = definitions(TWO_MILLENNIA / "map/definition.csv")
    result = {}
    for province_id, name in TWO_MILLENNIA_IDS.items():
        raw = ming.mask_for(translated, [defs[province_id]]) & land
        aligned = border.align_mask(raw, borders, land)
        thinned = play.gameplay_thin(aligned, borders)
        result[name] = border.dilate(thinned, 1) & border.dilate(aligned, 1) & land
    return result


def shanzhou_land_link(target: np.ndarray, target_defs: dict[int, tuple[int, int, int]]) -> np.ndarray:
    """Keep Shanzhou land-connected to both Huazhou and Luoyang."""
    guide = Image.new("L", (target.shape[1], target.shape[0]), 0)
    ImageDraw.Draw(guide).polygon(
        [(4517, 826), (4526, 826), (4535, 828), (4549, 829),
         (4549, 833), (4536, 835), (4527, 834), (4517, 832)],
        fill=255,
    )
    polygon = np.asarray(guide) > 0
    # Only reshape the old bottleneck.  Shanzhou absorbs mountain-edge and
    # Puzhou pixels plus a two-pixel-deep eastern gate, leaving the body of
    # Luoyang intact while guaranteeing a true four-way map adjacency.
    editable_ids = (4967, 1836, 5183, 5261, 5254, 5272)
    editable = ming.mask_for(target, [target_defs[province_id] for province_id in editable_ids])
    return polygon & editable


def guangzhou_dongguan_clearance(
    target: np.ndarray,
    target_defs: dict[int, tuple[int, int, int]],
) -> np.ndarray:
    """Protect the original Guangzhou–Dongguan land border from mountain masks."""
    guangzhou = ming.mask_for(target, [target_defs[667]])
    dongguan = ming.mask_for(target, [target_defs[4943]])
    shared_edge = (
        (guangzhou & border.dilate(dongguan, 1))
        | (dongguan & border.dilate(guangzhou, 1))
    )
    return border.dilate(shared_edge, 2) & (guangzhou | dongguan)


def touches(first: np.ndarray, second: np.ndarray) -> bool:
    return bool(
        (first[:, 1:] & second[:, :-1]).any()
        or (first[:, :-1] & second[:, 1:]).any()
        or (first[1:] & second[:-1]).any()
        or (first[:-1] & second[1:]).any()
    )


def candidate_colors(names: list[str], used: set[tuple[int, int, int]]):
    result = {}
    for index, name in enumerate(names, start=1):
        red = 32 + (index * 71) % 207
        green = 32 + (index * 113) % 207
        blue = 32 + (index * 157) % 207
        color = (red, green, blue)
        while color in used or color in result.values():
            color = ((color[0] + 17) % 224 + 16, (color[1] + 29) % 224 + 16, (color[2] + 43) % 224 + 16)
        result[name] = color
    return result


def axis(mask: np.ndarray) -> list[list[float]]:
    ys, xs = np.where(mask)
    points = np.column_stack((xs, ys)).astype(np.float64)
    center = points.mean(axis=0)
    if len(points) < 2:
        return [center.tolist(), center.tolist()]
    _, _, vectors = np.linalg.svd(points - center, full_matrices=False)
    direction = vectors[0]
    projected = (points - center) @ direction
    first = center + direction * projected.min()
    last = center + direction * projected.max()
    return [[round(float(first[0]), 2), round(float(first[1]), 2)], [round(float(last[0]), 2), round(float(last[1]), 2)]]


def font(size: int, bold: bool = False):
    path = Path("/System/Library/Fonts/PingFang.ttc")
    if path.exists():
        return ImageFont.truetype(str(path), size=size, index=1 if bold else 0)
    return ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", size=size)


def render() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    canonical = MOD / "map/provinces.bmp"
    before_hash = hashlib.sha256(canonical.read_bytes()).hexdigest()
    frozen_bitmap = ROOT / "planning/northwest_mountains/strategic_v1/pre_b38/map/provinces.bmp"
    frozen_definition = ROOT / "planning/northwest_mountains/strategic_v1/pre_b38/map/definition.csv"
    if frozen_bitmap.exists():
        original_mod = adapted.MOD
        adapted.MOD = frozen_bitmap.parents[1]
        target, land, base_masks = adapted.build_masks()
        adapted.MOD = original_mod
    else:
        target, land, base_masks = adapted.build_masks()
    borders = border.province_boundaries(target, land)
    impassable = current_impassable_mask(target)
    target_defs = definitions(frozen_definition if frozen_definition.exists() else MOD / "map/definition.csv")
    shanzhou_link = shanzhou_land_link(target, target_defs)
    city_clearance = guangzhou_dongguan_clearance(target, target_defs)

    masks: dict[str, np.ndarray] = {}
    status: dict[str, str] = {}
    source_ref: dict[str, str] = {}
    for province_id, name in MING_IDS.items():
        raw = base_masks[province_id]
        if province_id in adapted.CURRENT_EQUIVALENTS:
            masks[name] = largest_component(raw)
            status[name] = "现有锚点"
            source_ref[name] = f"当前省份 {adapted.CURRENT_EQUIVALENTS[province_id]}"
        else:
            aligned = border.align_mask(raw, borders, land)
            thin = play.gameplay_thin(aligned, borders)
            styled = border.dilate(thin, 1) & border.dilate(aligned, 1)
            thinned = largest_component(styled & land & ~impassable & ~shanzhou_link & ~city_clearance)
            # Tiny but strategically meaningful border ranges should remain
            # visible instead of collapsing into a decorative handful of pixels.
            masks[name] = (
                largest_component(aligned & land & ~impassable & ~shanzhou_link & ~city_clearance)
                if thinned.sum() < 20 else thinned
            )
            status[name] = "新增候选"
            source_ref[name] = f"大明日不落 {province_id}"

    for name, mask in load_two_millennia_masks(target.shape, land, borders).items():
        masks[name] = largest_component(mask & ~impassable & ~shanzhou_link & ~city_clearance)
        status[name] = "新增候选"
        source_id = next(pid for pid, candidate in TWO_MILLENNIA_IDS.items() if candidate == name)
        source_ref[name] = f"风云世纪两千年 {source_id}"

    # Existing anchors win every overlap.  New candidates are then assigned in
    # panel order, keeping each future impassable province one connected block.
    ordered_names = [name for group in GROUPS.values() for name in group]
    for name in ordered_names:
        masks[name] = largest_component(masks[name] & ~shanzhou_link & ~city_clearance)
    occupied = np.logical_or.reduce([masks[name] for name in ordered_names if status[name] == "现有锚点"])
    for name in ordered_names:
        if status[name] == "现有锚点":
            continue
        masks[name] = largest_component(masks[name] & ~occupied)
        if not masks[name].any():
            raise ValueError(f"Candidate {name} vanished after overlap resolution")
        occupied |= masks[name]

    # Reuse the project's gameplay cap for candidate geometry only.
    candidate = {index: masks[name].copy() for index, name in enumerate(ordered_names) if status[name] == "新增候选"}
    old_cap = play.MAX_PLAYABLE_COVERAGE
    play.MAX_PLAYABLE_COVERAGE = MAX_PLAYABLE_COVERAGE
    candidate, worst = play.cap_playable_coverage(candidate, target, borders)
    play.MAX_PLAYABLE_COVERAGE = old_cap
    for index, name in enumerate(ordered_names):
        if status[name] == "新增候选":
            masks[name] = largest_component(candidate[index])
            if not masks[name].any():
                raise ValueError(f"Candidate {name} vanished after coverage cap")

    new_names = [name for name in ordered_names if status[name] == "新增候选"]
    anchor_names = [name for name in ordered_names if status[name] == "现有锚点"]
    new_union = np.logical_or.reduce([masks[name] for name in new_names])
    actual_worst = 0.0
    for color in np.unique(target[new_union].reshape(-1, 3), axis=0):
        province = np.all(target == color, axis=2)
        total = int(province.sum())
        if total:
            actual_worst = max(actual_worst, float((new_union & province).sum()) / total)

    colors = candidate_colors(
        [name for name in ordered_names if status[name] == "新增候选"],
        set(target_defs.values()),
    )

    full = target.copy()
    shanzhou = ming.mask_for(target, [target_defs[4967]]) | shanzhou_link
    full[shanzhou_link] = target_defs[4967]
    for name in ordered_names:
        if status[name] == "新增候选":
            full[masks[name]] = colors[name]
    huazhou = ming.mask_for(target, [target_defs[5270]])
    luoyang = ming.mask_for(target, [target_defs[1836]])
    if largest_component(shanzhou).sum() != shanzhou.sum():
        raise RuntimeError("Shanzhou land-link adjustment fragmented Shanzhou")
    if not touches(shanzhou, huazhou) or not touches(shanzhou, luoyang):
        raise RuntimeError("Shanzhou does not connect Huazhou–Shanzhou–Luoyang")
    guangzhou = ming.mask_for(full, [target_defs[667]])
    dongguan = ming.mask_for(full, [target_defs[4943]])
    if not touches(guangzhou, dongguan):
        raise RuntimeError("Mountain masks block the Guangzhou–Dongguan land border")
    full_path = OUT / "han_strategic_mountains_v2_full_draft.bmp"
    Image.fromarray(full).save(full_path, format="BMP")
    crop_path = OUT / "han_strategic_mountains_v2_crop_draft.bmp"
    Image.fromarray(full).crop(CROP).save(crop_path, format="BMP")

    review = target.copy()
    group_for_name = {name: group for group, names in GROUPS.items() for name in names}
    for name in ordered_names:
        review[masks[name]] = GROUP_COLORS[group_for_name[name]]
    crop = Image.fromarray(review).crop(CROP)
    scale = 2
    shown = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 690, max(shown.height, 1120)), (245, 243, 237))
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    panel_x = shown.width + 24
    draw.text((panel_x, 22), "汉地不可通行山脉·战略核心稿", font=font(27, True), fill=(28, 29, 31))
    draw.text((panel_x, 64), "当前地图为底；大明日不落定主轴，风云两千年补燕山", font=font(15), fill=(70, 71, 73))
    draw.text((panel_x, 88), "山体适度加宽；保留陕州及广州—东莞的必要陆地邻接", font=font(15), fill=(70, 71, 73))

    y = 128
    for index, (group, names) in enumerate(GROUPS.items(), start=1):
        color = GROUP_COLORS[group]
        draw.rectangle((panel_x, y + 3, panel_x + 24, y + 27), fill=color, outline=(35, 35, 35))
        draw.text((panel_x + 36, y), f"{index}. {group}", font=font(19, True), fill=(31, 32, 34))
        line = "、".join(names)
        chunks = []
        while line:
            chunks.append(line[:31])
            line = line[31:]
        for offset, chunk in enumerate(chunks):
            draw.text((panel_x + 36, y + 29 + offset * 22), chunk, font=font(14), fill=(68, 69, 71))
        y += 65 + len(chunks) * 22

    draw.text((panel_x, 790), f"现有锚点：{len(anchor_names)} 段；新增候选：{len(new_names)} 段", font=font(15), fill=(59, 60, 62))
    draw.text((panel_x, 817), f"新增候选像素：{int(new_union.sum()):,}；单省建议上限：{MAX_PLAYABLE_COVERAGE:.0%}", font=font(15), fill=(59, 60, 62))
    draw.text((panel_x, 844), f"成品最高侵占约：{actual_worst:.0%}；每段均为四向连通块", font=font(15), fill=(59, 60, 62))
    draw.text((panel_x, 871), "不绘制关道；广州与东莞保持直接陆地邻接。", font=font(15), fill=(59, 60, 62))
    draw.text((panel_x, 898), "评审 BMP；正式 provinces.bmp 未修改。", font=font(15), fill=(117, 66, 48))
    annotated_path = OUT / "han_strategic_mountains_v2_annotated.png"
    canvas.save(annotated_path)

    features = []
    manifest = ["name\tgroup\tstatus\tsource\trgb\tpixels\tbbox"]
    for name in ordered_names:
        mask = masks[name]
        ys, xs = np.where(mask)
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        rgb = colors.get(name)
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "group": group_for_name[name],
                "status": status[name],
                "source": source_ref[name],
                "candidate_rgb": list(rgb) if rgb else None,
                "pixel_crs": "EU4 provinces.bmp top-left origin",
            },
            "geometry": {"type": "LineString", "coordinates": axis(mask)},
        })
        manifest.append(
            f"{name}\t{group_for_name[name]}\t{status[name]}\t{source_ref[name]}\t"
            f"{','.join(map(str, rgb)) if rgb else 'existing'}\t{int(mask.sum())}\t{','.join(map(str, bbox))}"
        )
    geojson_path = OUT / "han_strategic_mountains_v2_axes.geojson"
    geojson_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=2) + "\n")
    manifest_path = OUT / "han_strategic_mountains_v2_manifest.tsv"
    manifest_path.write_text("\n".join(manifest) + "\n")

    after_hash = hashlib.sha256(canonical.read_bytes()).hexdigest()
    if after_hash != before_hash:
        raise RuntimeError("Canonical provinces.bmp changed during review render")
    if Image.open(full_path).size != Image.open(canonical).size:
        raise RuntimeError("Full draft dimensions do not match canonical map")

    print(f"RANGES:{len(ordered_names)}; ANCHORS:{len(anchor_names)}; NEW:{len(new_names)}")
    print(f"NEW_PIXELS:{int(new_union.sum())}; WORST_COVERAGE:{actual_worst:.4f}")
    print(f"CANONICAL_SHA256:{after_hash}")
    for path in (full_path, crop_path, annotated_path, geojson_path, manifest_path):
        print(path)


if __name__ == "__main__":
    render()
