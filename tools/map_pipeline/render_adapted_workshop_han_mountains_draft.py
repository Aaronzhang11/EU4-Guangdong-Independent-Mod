#!/usr/bin/env python3
"""Adapt the 1728520255 workshop mountain layout to the current mod map.

This remains a review-only render. Existing impassable ranges already present in
the current map are used as anchors; missing ranges are resized from the source
geometry, clipped to current land, and drawn with review colours.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render_workshop_han_impassable_draft as source_draft


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
OUT = ROOT / "planning/han_mountains/workshop_adapted"
CROP = source_draft.CROP

# Source ranges for which this mod already has a purpose-built equivalent.
# These current shapes are retained instead of laying a second mountain on top.
CURRENT_EQUIVALENTS = {
    5146: 5029,  # Taiwan central range
    5175: 5175, 5176: 5176, 5183: 5183, 5187: 5187,  # Qin–Shu barriers
    5177: 5257, 5178: 5258, 5179: 5259,  # Hengshan / Taihang
    5181: 5260, 5180: 5261,  # Luliang / Zhongtiao
}

# Per-range scaling around the source shape's own centre. Values are modest:
# long ranges mainly gain width, while tiny source polygons gain enough body to
# remain legible among the current mod's much denser provinces.
TRANSFORMS = {
    5147: (1.20, 1.12, 8, -1),
    5152: (1.12, 1.25, -2, 0),
    5154: (1.08, 1.12, -2, 0),
    5155: (1.05, 1.12, -3, 0),
    5156: (0.96, 1.02, -4, 0),
    5157: (1.22, 1.25, -2, 0),
    5158: (1.10, 1.05, -2, 0),
    5159: (1.35, 1.30, 0, 0),
    5160: (1.25, 1.22, 0, 0),
    5161: (1.08, 1.18, 0, 0),
    5162: (1.50, 1.20, 0, 0),
    5163: (1.22, 1.45, 0, 0),
    5164: (1.10, 1.10, 0, 0),
    5165: (1.35, 1.35, 4, 0),
    5166: (1.18, 1.18, 3, 0),
    5167: (1.30, 1.25, 5, -1),
    5168: (1.14, 1.12, 7, 0),
    5169: (1.65, 1.30, 5, 0),
    5170: (1.08, 1.05, 5, 0),
    5171: (1.04, 1.12, 7, 0),
    5172: (1.65, 1.30, 4, 0),
    5173: (1.22, 1.22, 3, 0),
    5174: (1.35, 1.30, 3, 0),
    5182: (1.08, 1.16, 5, 0),
    5237: (1.12, 1.18, 1, 0),
}


def numeric_block(text: str, key: str) -> set[int]:
    match = re.search(rf"(?ms)^\s*{re.escape(key)}\s*=\s*\{{(.*?)^\s*\}}", text)
    if not match:
        return set()
    clean = re.sub(r"#.*", "", match.group(1))
    return {int(value) for value in re.findall(r"\b\d+\b", clean)}


def resized_mask(mask: np.ndarray, transform: tuple[float, float, int, int]) -> np.ndarray:
    ys, xs = np.where(mask)
    if not len(xs):
        return mask.copy()
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    sx, sy, dx, dy = transform
    crop = Image.fromarray((mask[y0:y1, x0:x1] * 255).astype(np.uint8), mode="L")
    width = max(1, round(crop.width * sx))
    height = max(1, round(crop.height * sy))
    scaled = np.asarray(crop.resize((width, height), Image.Resampling.NEAREST)) > 0
    cx, cy = (x0 + x1) / 2 + dx, (y0 + y1) / 2 + dy
    left, top = round(cx - width / 2), round(cy - height / 2)
    result = np.zeros_like(mask)
    tx0, ty0 = max(0, left), max(0, top)
    tx1, ty1 = min(mask.shape[1], left + width), min(mask.shape[0], top + height)
    sx0, sy0 = tx0 - left, ty0 - top
    result[ty0:ty1, tx0:tx1] = scaled[sy0:sy0 + ty1 - ty0, sx0:sx0 + tx1 - tx0]
    return result


def build_masks() -> tuple[np.ndarray, np.ndarray, dict[int, np.ndarray]]:
    target = np.asarray(Image.open(MOD / "map/provinces.bmp").convert("RGB"))
    source = np.asarray(Image.open(source_draft.SOURCE / "map/provinces.bmp").convert("RGB"))
    translated = source[
        source_draft.SOURCE_Y_OFFSET:source_draft.SOURCE_Y_OFFSET + target.shape[0],
        source_draft.SOURCE_X_OFFSET:source_draft.SOURCE_X_OFFSET + target.shape[1],
    ]
    source_defs = source_draft.definitions(source_draft.SOURCE / "map/definition.csv")
    target_defs = source_draft.definitions(MOD / "map/definition.csv")

    default_text = (MOD / "map/default.map").read_text(encoding="cp1252", errors="replace")
    water_ids = numeric_block(default_text, "sea_starts") | numeric_block(default_text, "lakes")
    water_colors = [target_defs[province_id] for province_id in water_ids if province_id in target_defs]
    land = ~source_draft.mask_for(target, water_colors)

    masks: dict[int, np.ndarray] = {}
    for source_id in source_draft.NAMES:
        equivalent = CURRENT_EQUIVALENTS.get(source_id)
        if equivalent is not None:
            masks[source_id] = source_draft.mask_for(target, [target_defs[equivalent]])
            continue
        raw = source_draft.mask_for(translated, [source_defs[source_id]])
        masks[source_id] = resized_mask(raw, TRANSFORMS[source_id]) & land

    return target, land, masks


def render() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    target, land, masks = build_masks()

    # Preserve the core of every range where resized candidates touch. This is
    # a legibility safeguard for the preview; final province IDs are assigned
    # only after approval.
    group_for_id = {
        province_id: group
        for group, province_ids in source_draft.GROUPS.items()
        for province_id in province_ids
    }
    review = target.copy()
    for province_id, mask in masks.items():
        review[mask] = source_draft.GROUP_COLORS[group_for_id[province_id]]

    full_path = OUT / "adapted_han_mountains_full_draft.bmp"
    Image.fromarray(review).save(full_path, format="BMP")
    crop_path = OUT / "adapted_han_mountains_crop_draft.bmp"
    Image.fromarray(review).crop(CROP).save(crop_path, format="BMP")

    crop = Image.fromarray(review).crop(CROP)
    scale = 2
    shown = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 650, max(shown.height, 920)), (244, 242, 236))
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 19)
    small = ImageFont.truetype(font_path, 15)
    panel_x = shown.width + 24
    draw.text((panel_x, 22), "汉地不可通行山脉·适配草图", font=title, fill=(30, 31, 33))
    draw.text((panel_x, 65), "以大明日不落轮廓为底稿，按当前地图调整宽度与位置", font=small, fill=(69, 70, 72))
    draw.text((panel_x, 90), "现有秦蜀、山西、台湾山脉沿用；所有新增轮廓避开水域", font=small, fill=(69, 70, 72))

    y = 138
    for index, (group, province_ids) in enumerate(source_draft.GROUPS.items(), 1):
        color = source_draft.GROUP_COLORS[group]
        draw.rectangle((panel_x, y + 4, panel_x + 24, y + 28), fill=color, outline=(35, 35, 35))
        draw.text((panel_x + 36, y), f"{index}. {group}", font=body, fill=(32, 33, 35))
        names = "、".join(source_draft.NAMES[province_id] for province_id in province_ids)
        lines, current = [], ""
        for part in names.split("、"):
            candidate = part if not current else current + "、" + part
            if len(candidate) > 27:
                lines.append(current)
                current = part
            else:
                current = candidate
        if current:
            lines.append(current)
        for offset, line in enumerate(lines):
            draw.text((panel_x + 36, y + 29 + offset * 22), line, font=small, fill=(70, 71, 73))
        y += 67 + 22 * len(lines)

    new_pixels = int(np.logical_or.reduce([masks[i] for i in masks if i not in CURRENT_EQUIVALENTS]).sum())
    anchored_pixels = int(np.logical_or.reduce([masks[i] for i in CURRENT_EQUIVALENTS]).sum())
    draw.text((panel_x, 805), f"新增适配轮廓：{new_pixels:,} 像素", font=small, fill=(61, 62, 64))
    draw.text((panel_x, 832), f"沿用现有山脉：{anchored_pixels:,} 像素", font=small, fill=(61, 62, 64))
    draw.text((panel_x, 859), "本图仍是审稿草图，未修改正式 provinces.bmp。", font=small, fill=(61, 62, 64))
    annotated_path = OUT / "adapted_han_mountains_annotated.png"
    canvas.save(annotated_path)

    print(f"RANGES:{len(masks)}; NEW_PIXELS:{new_pixels}; ANCHORED_PIXELS:{anchored_pixels}")
    print(full_path)
    print(crop_path)
    print(annotated_path)


if __name__ == "__main__":
    render()
