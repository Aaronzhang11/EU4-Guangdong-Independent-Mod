#!/usr/bin/env python3
"""Render a review-only northwest China impassable-mountain draft.

The current mod bitmap remains canonical and read-only.  Named axes come from
workshop 2935149060; workshop 1728520255 is used only as nearby silhouette
support before every mask is snapped to the current province borders.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import render_adapted_workshop_han_mountains_draft as adapted
import render_border_aligned_han_mountains_draft as border
import render_han_strategic_mountains_v2 as han
import render_playability_han_mountains_draft as play
import render_workshop_han_impassable_draft as ming


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
OUT = ROOT / "planning/northwest_mountains/strategic_v1"
DAMING = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
TWO_MILLENNIA = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/2935149060"
)
SOURCE_X_OFFSET = 438
SOURCE_Y_OFFSET = 9
CROP = (3850, 500, 4560, 930)
WORK = (3800, 470, 4620, 970)
MAX_PLAYABLE_COVERAGE = 0.36


GROUPS: dict[str, tuple[tuple[int, str], ...]] = {
    "北庭天山": (
        (3136, "阿尔泰山"), (5176, "塔尔巴哈台山"), (5172, "阿拉套山"),
        (5171, "外伊犁山"), (5177, "乌孙山西段"), (5178, "乌孙山东段"),
        (5170, "博罗科努山"), (5151, "天山中段"), (5158, "天山东段"),
        (5173, "巴里坤山"), (5174, "哈尔里克山"), (5175, "北塔山"),
    ),
    "昆仑南缘": (
        (5163, "喀喇昆仑山"), (5169, "昆仑山西段"), (4975, "昆仑山中段"),
        (5552, "昆仑山东段"), (4986, "祁曼塔格山"),
    ),
    "河西祁连": (
        (5553, "青海南山"), (5290, "祁连山"), (5368, "合黎山"),
        (5369, "龙首山"), (5371, "马鬃山西段"), (5372, "马鬃山东段"),
    ),
    "河湟朔漠": (
        (5551, "拉脊山"), (5550, "积石山"), (5549, "阿尼玛卿山"),
        (-1, "贺兰山"), (5114, "狼山"), (5082, "阴山西段"),
    ),
}

GROUP_COLORS = {
    "北庭天山": (62, 68, 78),
    "昆仑南缘": (88, 82, 92),
    "河西祁连": (122, 105, 88),
    "河湟朔漠": (97, 105, 103),
}

# Current impassable provinces kept as the dark foundation in the review.
CURRENT_ANCHORS = (1784, 1785, 1786, 2129, 2194, 4522, 5187)


def translated(path: Path, target_shape: tuple[int, ...]) -> np.ndarray:
    source = np.asarray(Image.open(path).convert("RGB"))
    x0, y0, x1, y1 = WORK
    result = source[
        SOURCE_Y_OFFSET + y0:SOURCE_Y_OFFSET + y1,
        SOURCE_X_OFFSET + x0:SOURCE_X_OFFSET + x1,
    ]
    if result.shape != target_shape:
        raise ValueError(f"Translated source has {result.shape}, expected {target_shape}")
    return result


def land_mask(target: np.ndarray, defs: dict[int, tuple[int, int, int]]) -> np.ndarray:
    default = (MOD / "map/default.map").read_text(encoding="cp1252", errors="replace")
    water_ids = adapted.numeric_block(default, "sea_starts") | adapted.numeric_block(default, "lakes")
    return ~ming.mask_for(target, [defs[i] for i in water_ids if i in defs])


def reference_impassable(values: np.ndarray, root: Path) -> np.ndarray:
    defs = han.definitions(root / "map/definition.csv")
    climate = (root / "map/climate.txt").read_text(encoding="cp1252", errors="replace")
    ids = adapted.numeric_block(climate, "impassable")
    return ming.mask_for(values, [defs[i] for i in ids if i in defs])


def connected(mask: np.ndarray) -> bool:
    return bool(mask.any() and han.largest_component(mask).sum() == mask.sum())


def wrap_names(names: list[str], limit: int = 27) -> list[str]:
    lines: list[str] = []
    current = ""
    for name in names:
        candidate = name if not current else current + "、" + name
        if len(candidate) > limit:
            lines.append(current)
            current = name
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def render() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    canonical = MOD / "map/provinces.bmp"
    before_hash = hashlib.sha256(canonical.read_bytes()).hexdigest()
    frozen_bitmap = OUT / "pre_b38/map/provinces.bmp"
    frozen_definition = OUT / "pre_b38/map/definition.csv"
    review_base = frozen_bitmap if frozen_bitmap.exists() else canonical
    definition_base = frozen_definition if frozen_definition.exists() else MOD / "map/definition.csv"
    target_full = np.asarray(Image.open(review_base).convert("RGB"))
    wx0, wy0, wx1, wy1 = WORK
    target = target_full[wy0:wy1, wx0:wx1].copy()
    target_defs = han.definitions(definition_base)
    land = land_mask(target, target_defs)
    borders = border.province_boundaries(target, land)
    existing_impassable = han.current_impassable_mask(target)

    two = translated(TWO_MILLENNIA / "map/provinces.bmp", target.shape)
    daming = translated(DAMING / "map/provinces.bmp", target.shape)
    two_defs = han.definitions(TWO_MILLENNIA / "map/definition.csv")
    daming_support = reference_impassable(daming, DAMING)

    group_for_name = {
        name: group for group, entries in GROUPS.items() for _, name in entries
    }
    source_for_name = {
        name: province_id for entries in GROUPS.values() for province_id, name in entries
    }
    ordered_names = [name for entries in GROUPS.values() for _, name in entries]
    raw_axes: dict[str, np.ndarray] = {}
    masks: dict[str, np.ndarray] = {}
    covered: list[str] = []
    border_band = border.dilate(borders, 2)

    for name in ordered_names:
        province_id = source_for_name[name]
        if name == "贺兰山":
            # The reference mods do not provide a dependable Helan polygon.
            # Use this mod's exact Alxa–Ningxia/Zhongwei shared border instead.
            alxa = ming.mask_for(target, [target_defs[709]])
            ningxia_plain = ming.mask_for(target, [target_defs[698], target_defs[5286]])
            raw = (
                (alxa & border.dilate(ningxia_plain, 1))
                | (ningxia_plain & border.dilate(alxa, 1))
            ) & land
        else:
            raw = ming.mask_for(two, [two_defs[province_id]]) & land
        raw_axes[name] = han.largest_component(raw)
        # Daming is not copied wholesale: only pixels immediately supporting a
        # named Two-Millennia axis can add body to that axis.
        supported = raw if name == "贺兰山" else raw | (daming_support & border.dilate(raw, 3))
        aligned = border.align_mask(supported, borders, land)
        thin = play.gameplay_thin(aligned, borders)
        # Keep the visible mountain body inside a two-pixel province-border
        # band.  This is stricter than the Han draft and avoids long strokes
        # wandering through the centre of large northwestern provinces.
        styled = border.dilate(thin, 1) & border.dilate(aligned, 2) & border_band
        candidate = han.largest_component(styled & land & ~existing_impassable)
        if int(candidate.sum()) < 12:
            covered.append(name)
            continue
        masks[name] = candidate

    # Resolve candidate overlaps in geographic order and keep one four-way
    # component per future impassable province.
    occupied = existing_impassable.copy()
    for name in ordered_names:
        if name not in masks:
            continue
        masks[name] = han.largest_component(masks[name] & ~occupied)
        if int(masks[name].sum()) < 8:
            covered.append(name)
            del masks[name]
            continue
        occupied |= masks[name]

    candidate_by_index = {i: masks[name].copy() for i, name in enumerate(ordered_names) if name in masks}
    old_cap = play.MAX_PLAYABLE_COVERAGE
    play.MAX_PLAYABLE_COVERAGE = MAX_PLAYABLE_COVERAGE
    candidate_by_index, _ = play.cap_playable_coverage(candidate_by_index, target, borders)
    play.MAX_PLAYABLE_COVERAGE = old_cap
    for i, name in enumerate(ordered_names):
        if name in masks:
            masks[name] = han.largest_component(candidate_by_index[i])
            if not masks[name].any():
                raise RuntimeError(f"Coverage cap erased {name}")

    new_names = [name for name in ordered_names if name in masks]
    colors = han.candidate_colors(new_names, set(target_defs.values()))
    local_full = target.copy()
    for name in new_names:
        local_full[masks[name]] = colors[name]

    full = target_full.copy()
    full[wy0:wy1, wx0:wx1] = local_full

    full_path = OUT / "northwest_strategic_mountains_full_draft.bmp"
    crop_path = OUT / "northwest_strategic_mountains_crop_draft.bmp"
    Image.fromarray(full).save(full_path, format="BMP")
    Image.fromarray(full).crop(CROP).save(crop_path, format="BMP")

    review = target.copy()
    anchor_colors = [target_defs[i] for i in CURRENT_ANCHORS if i in target_defs]
    review[ming.mask_for(target, anchor_colors)] = (48, 49, 53)
    for name in new_names:
        review[masks[name]] = GROUP_COLORS[group_for_name[name]]

    local_crop = (CROP[0] - wx0, CROP[1] - wy0, CROP[2] - wx0, CROP[3] - wy0)
    crop = Image.fromarray(review).crop(local_crop)
    scale = 2
    shown = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 650, max(960, shown.height)), (245, 243, 237))
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    panel_x = shown.width + 24
    draw.text((panel_x, 20), "中国西北不可通行山脉·战略草图", font=han.font(27, True), fill=(28, 29, 31))
    draw.text((panel_x, 62), "当前地图为底；风云两千年定细轴，大明日不落校验山体", font=han.font(15), fill=(68, 69, 71))
    draw.text((panel_x, 87), "沿现有省界吸附并适度增厚；不直接修改正式 provinces.bmp", font=han.font(15), fill=(68, 69, 71))

    y = 126
    for index, (group, entries) in enumerate(GROUPS.items(), start=1):
        color = GROUP_COLORS[group]
        draw.rectangle((panel_x, y + 3, panel_x + 24, y + 27), fill=color, outline=(35, 35, 35))
        draw.text((panel_x + 36, y), f"{index}. {group}", font=han.font(19, True), fill=(31, 32, 34))
        lines = wrap_names([name for _, name in entries])
        for offset, line in enumerate(lines):
            draw.text((panel_x + 36, y + 29 + offset * 22), line, font=han.font(14), fill=(68, 69, 71))
        y += 65 + len(lines) * 22

    new_union = np.logical_or.reduce([masks[name] for name in new_names])
    worst = 0.0
    for color in np.unique(target[new_union].reshape(-1, 3), axis=0):
        province = np.all(target == color, axis=2)
        total = int(np.all(target_full == color, axis=2).sum())
        if total:
            worst = max(worst, float((new_union & province).sum()) / total)
    draw.rectangle((panel_x, 730, panel_x + 24, 754), fill=(48, 49, 53), outline=(35, 35, 35))
    draw.text((panel_x + 36, 727), "现有不可通行底座（保留）", font=han.font(15), fill=(58, 59, 61))
    draw.text((panel_x, 772), f"参考轴线：{len(ordered_names)}；新增候选：{len(new_names)}；叠合现有：{len(set(covered))}", font=han.font(15), fill=(58, 59, 61))
    border_share = float((new_union & border_band).sum()) / max(1, int(new_union.sum()))
    draw.text((panel_x, 799), f"新增像素：{int(new_union.sum()):,}；省界带占比：{border_share:.0%}；最高侵占：{worst:.0%}", font=han.font(15), fill=(58, 59, 61))
    draw.text((panel_x, 826), "战略留口：准噶尔门、哈密口、河西走廊及河湟通路", font=han.font(15), fill=(58, 59, 61))
    draw.text((panel_x, 853), "评审稿；新山体尚未分配正式省份ID。", font=han.font(15), fill=(117, 66, 48))
    annotated_path = OUT / "northwest_strategic_mountains_annotated.png"
    canvas.save(annotated_path)

    features = []
    manifest = ["name\tgroup\tstatus\tsource_id\trgb\tpixels\tbbox"]
    for name in ordered_names:
        raw = raw_axes[name]
        final = masks.get(name)
        feature_mask = final if final is not None else raw
        ys, xs = np.where(feature_mask)
        status = "新增候选" if final is not None else "叠合现有底座"
        rgb = colors.get(name)
        bbox = [int(xs.min()) + wx0, int(ys.min()) + wy0, int(xs.max()) + wx0, int(ys.max()) + wy0]
        coordinates = [
            [round(point[0] + wx0, 2), round(point[1] + wy0, 2)]
            for point in han.axis(feature_mask)
        ]
        source_label = "当前709—698/5286省界" if name == "贺兰山" else str(source_for_name[name])
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "group": group_for_name[name],
                "status": status,
                "source_mod": "当前模组省界" if name == "贺兰山" else "风云世纪两千年",
                "source_id": source_label,
                "daming_support": final is not None,
                "candidate_rgb": list(rgb) if rgb else None,
                "pixel_crs": "EU4 provinces.bmp top-left origin",
            },
            "geometry": {"type": "LineString", "coordinates": coordinates},
        })
        manifest.append(
            f"{name}\t{group_for_name[name]}\t{status}\t{source_label}\t"
            f"{','.join(map(str, rgb)) if rgb else 'existing'}\t{int(feature_mask.sum())}\t{','.join(map(str, bbox))}"
        )
    geojson_path = OUT / "northwest_strategic_mountains_axes.geojson"
    geojson_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=2) + "\n")
    manifest_path = OUT / "northwest_strategic_mountains_manifest.tsv"
    manifest_path.write_text("\n".join(manifest) + "\n")

    plan_path = OUT / "plan.md"
    plan_path.write_text(
        "# 中国西北不可通行山脉战略草案\n\n"
        "以当前模组地图为唯一底图。风云世纪两千年提供细分山系轴线，大明日不落仅在同一轴线附近补足山体厚度；"
        "所有候选再吸附到当前省界，并限制单个可通行省份被侵占的比例。\n\n"
        "## 战略原则\n\n"
        "- 天山体系分隔准噶尔与塔里木，但保留准噶尔门、伊犁通路和哈密口。\n"
        "- 昆仑体系作为塔里木—青藏的硬边界，不额外封死绿洲链。\n"
        "- 祁连、合黎、龙首与马鬃山共同塑造河西走廊，山体可以厚，但走廊本身必须连续。\n"
        "- 贺兰山严格沿阿拉善—宁夏平原省界生成；拉脊、积石、阿尼玛卿强化河湟边缘，狼山、阴山控制宁夏—河套北口。\n"
        "- 本批仅为评审BMP，不写 definition.csv、climate.txt 或正式 provinces.bmp。\n",
        encoding="utf-8",
    )

    after_hash = hashlib.sha256(canonical.read_bytes()).hexdigest()
    if after_hash != before_hash:
        raise RuntimeError("Canonical provinces.bmp changed during draft render")
    if Image.open(full_path).size != Image.open(canonical).size:
        raise RuntimeError("Full draft dimensions differ from canonical bitmap")
    if not all(connected(masks[name]) for name in new_names):
        raise RuntimeError("A northwest candidate is not four-way connected")

    print(f"AXES:{len(ordered_names)}; NEW:{len(new_names)}; COVERED:{len(set(covered))}")
    print(f"NEW_PIXELS:{int(new_union.sum())}; WORST_COVERAGE:{worst:.4f}")
    print(f"CANONICAL_SHA256:{after_hash}")
    for path in (full_path, crop_path, annotated_path, geojson_path, manifest_path, plan_path):
        print(path)


if __name__ == "__main__":
    render()
