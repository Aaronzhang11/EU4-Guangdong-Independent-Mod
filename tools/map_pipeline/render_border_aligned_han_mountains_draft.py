#!/usr/bin/env python3
"""Redesign candidate Han mountain ranges so their margins follow province borders."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import render_adapted_workshop_han_mountains_draft as adapted
import render_workshop_han_impassable_draft as source_draft


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "planning/han_mountains/border_aligned"
CROP = source_draft.CROP


def province_boundaries(values: np.ndarray, land: np.ndarray) -> np.ndarray:
    """Return land-to-land RGB boundaries, excluding coasts and waterways."""
    boundary = np.zeros(values.shape[:2], dtype=bool)
    horizontal = np.any(values[:, 1:] != values[:, :-1], axis=2) & land[:, 1:] & land[:, :-1]
    vertical = np.any(values[1:] != values[:-1], axis=2) & land[1:] & land[:-1]
    boundary[:, 1:] |= horizontal
    boundary[:, :-1] |= horizontal
    boundary[1:] |= vertical
    boundary[:-1] |= vertical
    return boundary


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    image = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    return np.asarray(image.filter(ImageFilter.MaxFilter(radius * 2 + 1))) > 0


def erode(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    image = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    return np.asarray(image.filter(ImageFilter.MinFilter(radius * 2 + 1))) > 0


def align_mask(mask: np.ndarray, borders: np.ndarray, land: np.ndarray) -> np.ndarray:
    """Keep a central spine, but replace the outer margin with nearby borders."""
    ys, xs = np.where(mask)
    if not len(xs):
        return mask.copy()
    padding = 12
    x0, x1 = max(0, int(xs.min()) - padding), min(mask.shape[1], int(xs.max()) + padding + 1)
    y0, y1 = max(0, int(ys.min()) - padding), min(mask.shape[0], int(ys.max()) + padding + 1)
    local = mask[y0:y1, x0:x1]
    local_borders = borders[y0:y1, x0:x1]
    local_land = land[y0:y1, x0:x1]

    # The inner spine prevents the range from breaking apart. Its outer shell is
    # replaced by a 5-pixel search for nearby province boundaries, producing the
    # stair-stepped, administrative-border-following silhouette requested.
    core = erode(local, 1)
    search_shell = dilate(local, 2) & ~erode(local, 2)
    snapped_edge = dilate(local_borders & search_shell, 1)
    result_local = (core | snapped_edge) & dilate(local, 2) & local_land

    # Very small source ranges can erode completely. Retain their centre rather
    # than dropping a named range from the plan.
    if result_local.sum() < max(12, local.sum() * 0.35):
        result_local |= erode(local, 1)
    result = np.zeros_like(mask)
    result[y0:y1, x0:x1] = result_local
    return result


def render() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    target, land, masks = adapted.build_masks()
    borders = province_boundaries(target, land)

    aligned: dict[int, np.ndarray] = {}
    for province_id, mask in masks.items():
        if province_id in adapted.CURRENT_EQUIVALENTS:
            aligned[province_id] = mask
        else:
            aligned[province_id] = align_mask(mask, borders, land)

    group_for_id = {
        province_id: group
        for group, province_ids in source_draft.GROUPS.items()
        for province_id in province_ids
    }
    review = target.copy()
    for province_id, mask in aligned.items():
        review[mask] = source_draft.GROUP_COLORS[group_for_id[province_id]]

    full_path = OUT / "border_aligned_han_mountains_full_draft.bmp"
    crop_path = OUT / "border_aligned_han_mountains_crop_draft.bmp"
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
    draw.text((panel_x, 22), "汉地不可通行山脉·省界贴合稿", font=title, fill=(30, 31, 33))
    draw.text((panel_x, 65), "山系方向继承大明日不落，外缘改随当前省界延伸", font=small, fill=(69, 70, 72))
    draw.text((panel_x, 90), "保留山脉内部脊线，避免为了贴边而断裂或变成零散色块", font=small, fill=(69, 70, 72))

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

    new_ids = [province_id for province_id in aligned if province_id not in adapted.CURRENT_EQUIVALENTS]
    before = int(np.logical_or.reduce([masks[i] for i in new_ids]).sum())
    after = int(np.logical_or.reduce([aligned[i] for i in new_ids]).sum())
    edge_pixels = int(np.logical_or.reduce([aligned[i] & dilate(borders, 2) for i in new_ids]).sum())
    union_pixels = max(1, int(np.logical_or.reduce([aligned[i] for i in new_ids]).sum()))
    draw.text((panel_x, 805), f"调整前／调整后：{before:,}／{after:,} 像素", font=small, fill=(61, 62, 64))
    draw.text((panel_x, 832), f"贴近省界的新增山脉像素：{edge_pixels / union_pixels:.0%}", font=small, fill=(61, 62, 64))
    draw.text((panel_x, 859), "本图仍是审稿草图，未修改正式 provinces.bmp。", font=small, fill=(61, 62, 64))
    annotated_path = OUT / "border_aligned_han_mountains_annotated.png"
    canvas.save(annotated_path)

    print(f"RANGES:{len(aligned)}; BEFORE:{before}; AFTER:{after}; BORDER_SHARE:{edge_pixels / union_pixels:.4f}")
    print(full_path)
    print(crop_path)
    print(annotated_path)


if __name__ == "__main__":
    render()
