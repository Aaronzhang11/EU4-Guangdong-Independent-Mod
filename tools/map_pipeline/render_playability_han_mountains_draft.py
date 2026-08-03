#!/usr/bin/env python3
"""Render a thinner, province-border-aware mountain plan for gameplay review."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render_adapted_workshop_han_mountains_draft as adapted
import render_border_aligned_han_mountains_draft as border_aligned
import render_workshop_han_impassable_draft as source_draft


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "planning/han_mountains/playability_refined"
CROP = source_draft.CROP

# Stronger reductions for existing barriers most likely to close a route. The
# keys are source-plan IDs; CURRENT_EQUIVALENTS resolves them to current IDs.
EXISTING_EROSION = {
    5175: 1,  # Daba
    5176: 1,  # Minshan
    5177: 0,  # Hengshan is already small
    5178: 1,  # North Taihang
    5179: 1,  # South Taihang
    5180: 2,  # Zhongtiao: strongest reduction for the Henan/Shanxi passage
    5181: 1,  # Luliang
    5183: 1,  # Qinling
    5187: 0,  # Longshan is already narrow
    5146: 0,  # Existing Taiwan central range
}

MAX_PLAYABLE_COVERAGE = 0.30


def safe_erode(mask: np.ndarray, radius: int, minimum_ratio: float = 0.38) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    reduced = border_aligned.erode(mask, radius)
    if reduced.sum() >= max(8, mask.sum() * minimum_ratio):
        return reduced
    if radius > 1:
        reduced = border_aligned.erode(mask, 1)
        if reduced.sum() >= max(8, mask.sum() * minimum_ratio):
            return reduced
    return mask.copy()


def gameplay_thin(mask: np.ndarray, borders: np.ndarray) -> np.ndarray:
    """Favor a narrow border-hugging line while retaining a connected core."""
    # Keep the exact border pixels, not the former two-sided border band. This
    # prevents narrow southeastern provinces from losing a broad strip on both
    # sides of every administrative boundary.
    near_border = mask & borders
    core = border_aligned.erode(mask, 1)
    reduced = near_border | core
    if reduced.sum() < max(8, mask.sum() * 0.25):
        return mask.copy()
    return reduced


def cap_playable_coverage(
    masks: dict[int, np.ndarray], target: np.ndarray, borders: np.ndarray
) -> tuple[dict[int, np.ndarray], float]:
    """Keep any ordinary province from losing most of its pixels to mountains."""
    target_defs = source_draft.definitions(adapted.MOD / "map/definition.csv")
    climate = (adapted.MOD / "map/climate.txt").read_text(encoding="cp1252", errors="replace")
    impassable = adapted.numeric_block(climate, "impassable")
    rgb_to_id = {rgb: province_id for province_id, rgb in target_defs.items()}
    union = np.logical_or.reduce(list(masks.values()))
    colors = np.unique(target[union].reshape(-1, 3), axis=0)
    result = masks
    border_bands = [borders]
    border_bands.extend(border_aligned.dilate(borders, radius) for radius in (1, 2, 3))

    for color_value in colors:
        rgb = tuple(int(value) for value in color_value)
        target_id = rgb_to_id.get(rgb)
        if target_id is None or target_id in impassable:
            continue
        province = np.all(target == color_value, axis=2)
        total = int(province.sum())
        occupied = union & province
        count = int(occupied.sum())
        limit = max(6, int(total * MAX_PLAYABLE_COVERAGE))
        if count <= limit:
            continue

        # Find the widest province-border band that remains under the cap. If
        # even the exact one-pixel boundary is above it, keep that boundary: a
        # coherent thin line is preferable to a dotted or disconnected range.
        exact = occupied & border_bands[0]
        keep = exact
        if int(exact.sum()) <= limit:
            for band in border_bands[1:]:
                candidate = occupied & band
                if int(candidate.sum()) <= limit:
                    keep = candidate
                else:
                    break
        remove = occupied & ~keep
        if remove.any():
            for province_id in result:
                result[province_id][remove] = False
            union[remove] = False

    worst = 0.0
    for color_value in colors:
        rgb = tuple(int(value) for value in color_value)
        target_id = rgb_to_id.get(rgb)
        if target_id is None or target_id in impassable:
            continue
        province = np.all(target == color_value, axis=2)
        total = int(province.sum())
        if total:
            worst = max(worst, float((union & province).sum()) / total)
    return result, worst


def render() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    target, land, base_masks = adapted.build_masks()
    borders = border_aligned.province_boundaries(target, land)

    border_masks: dict[int, np.ndarray] = {}
    refined: dict[int, np.ndarray] = {}
    for province_id, mask in base_masks.items():
        if province_id in adapted.CURRENT_EQUIVALENTS:
            aligned = mask
            final = safe_erode(mask, EXISTING_EROSION[province_id])
        else:
            aligned = border_aligned.align_mask(mask, borders, land)
            final = gameplay_thin(aligned, borders)
        border_masks[province_id] = aligned
        refined[province_id] = final & land

    refined, worst_coverage = cap_playable_coverage(refined, target, borders)

    group_for_id = {
        province_id: group
        for group, province_ids in source_draft.GROUPS.items()
        for province_id in province_ids
    }
    review = target.copy()
    for province_id, mask in refined.items():
        review[mask] = source_draft.GROUP_COLORS[group_for_id[province_id]]

    full_path = OUT / "playability_refined_han_mountains_full_draft.bmp"
    crop_path = OUT / "playability_refined_han_mountains_crop_draft.bmp"
    Image.fromarray(review).save(full_path, format="BMP")
    Image.fromarray(review).crop(CROP).save(crop_path, format="BMP")

    scale = 2
    shown = Image.fromarray(review).crop(CROP).resize(
        ((CROP[2] - CROP[0]) * scale, (CROP[3] - CROP[1]) * scale),
        Image.Resampling.NEAREST,
    )
    canvas = Image.new("RGB", (shown.width + 650, 920), (244, 242, 236))
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 19)
    small = ImageFont.truetype(font_path, 15)
    panel_x = shown.width + 24
    draw.text((panel_x, 22), "汉地不可通行山脉·战略收窄稿", font=title, fill=(30, 31, 33))
    draw.text((panel_x, 65), "继续沿省界布局，但减少对可通行省份的侵占", font=small, fill=(69, 70, 72))
    draw.text((panel_x, 90), "中条山重点收窄；秦岭、大巴与太行保留绕行空间", font=small, fill=(69, 70, 72))

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

    before_union = np.logical_or.reduce(list(border_masks.values()))
    after_union = np.logical_or.reduce(list(refined.values()))
    before, after = int(before_union.sum()), int(after_union.sum())
    zhong_before = int(border_masks[5180].sum())
    zhong_after = int(refined[5180].sum())
    draw.text((panel_x, 786), f"全山系收窄：{before:,} → {after:,} 像素（−{1-after/before:.0%}）", font=small, fill=(61, 62, 64))
    draw.text((panel_x, 813), f"中条山：{zhong_before} → {zhong_after} 像素", font=small, fill=(61, 62, 64))
    draw.text((panel_x, 840), "设计原则：山脉形成方向性阻隔，不封死整块省份。", font=small, fill=(61, 62, 64))
    draw.text((panel_x, 867), f"可通行省份最高占用约 {worst_coverage:.0%}；正式地图未修改。", font=small, fill=(61, 62, 64))
    annotated_path = OUT / "playability_refined_han_mountains_annotated.png"
    canvas.save(annotated_path)

    print(f"RANGES:{len(refined)}; BEFORE:{before}; AFTER:{after}; ZHONGTIAO:{zhong_before}->{zhong_after}; WORST:{worst_coverage:.4f}")
    print(full_path)
    print(crop_path)
    print(annotated_path)


if __name__ == "__main__":
    render()
