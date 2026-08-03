#!/usr/bin/env python3
"""Render a combined Minshan/Daba strategic-barrier preview."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import apply_workshop_hebei_transplant as common


ROOT = Path(__file__).resolve().parents[2]
TARGET_MAP = ROOT / "guangdong_independent_practice/map"
SOURCE_MAP = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255/map"
)
OUT = ROOT / "planning/minshan_daba"
SOURCE_X_OFFSET = 423
SOURCE_Y_OFFSET = 11
DABA_SHIFT_X = -4
DABA_SHIFT_Y = -8
MINSHAN_ID, DABA_ID = 5176, 5175
MINSHAN_COLOUR, DABA_COLOUR = (166, 234, 140), (223, 27, 118)


def shifted(mask, dx, dy):
    result = np.zeros(mask.shape, dtype=bool)
    y0, y1 = max(0, dy), min(mask.shape[0], mask.shape[0] + dy)
    x0, x1 = max(0, dx), min(mask.shape[1], mask.shape[1] + dx)
    result[y0:y1, x0:x1] = mask[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    target = np.asarray(Image.open(TARGET_MAP / "provinces.bmp").convert("RGB"))
    source = np.asarray(Image.open(SOURCE_MAP / "provinces.bmp").convert("RGB"))
    source_defs, _ = common.read_definitions(SOURCE_MAP / "definition.csv")
    translated = source[
        SOURCE_Y_OFFSET:SOURCE_Y_OFFSET + target.shape[0],
        SOURCE_X_OFFSET:SOURCE_X_OFFSET + target.shape[1],
    ]
    minshan = np.all(translated == source_defs[MINSHAN_ID][0], axis=2)
    daba_original = np.all(translated == source_defs[DABA_ID][0], axis=2)

    # Pull the source outline inward by one pixel. This preserves its course
    # while reducing the footprint on the dense Sichuan/Hubei province mesh.
    daba = daba_original.copy()
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        daba &= np.roll(daba_original, (dy, dx), axis=(0, 1))

    # Three 5-pixel-wide north/south corridors divide the narrowed ridge into
    # four strategic sections.
    yy, xx = np.indices(daba_original.shape)
    for centre_x in (4462, 4490, 4528):
        daba &= ~((np.abs(xx - centre_x) <= 2) & (yy >= 850) & (yy <= 900))
    daba = shifted(daba, DABA_SHIFT_X, DABA_SHIFT_Y)

    draft = target.copy()
    affected_mask = minshan | daba
    affected_colours = np.unique(target[affected_mask].reshape(-1, 3), axis=0)
    draft[minshan] = MINSHAN_COLOUR
    draft[daba] = DABA_COLOUR
    cleaned = np.zeros(affected_mask.shape, dtype=bool)

    for colour_array in affected_colours:
        colour = tuple(colour_array)
        comps = common.components(np.all(draft == colour, axis=2))
        if len(comps) <= 1:
            continue
        keep = max(comps, key=len)
        for comp in comps:
            if comp is keep:
                continue
            neighbours = []
            for x, y in comp:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < draft.shape[1] and 0 <= ny < draft.shape[0]:
                        candidate = tuple(draft[ny, nx])
                        if candidate != colour:
                            neighbours.append(candidate)
            replacement = Counter(neighbours).most_common(1)[0][0]
            for x, y in comp:
                draft[y, x] = replacement
                cleaned[y, x] = True

    Image.fromarray(draft).save(OUT / "minshan_daba_strategy_full_draft.bmp")
    x0, x1, y0, y1 = 4388, 4570, 795, 910
    crop = draft[y0:y1 + 1, x0:x1 + 1]
    Image.fromarray(crop).save(OUT / "minshan_daba_strategy_draft.bmp")

    review = crop.copy()
    review[minshan[y0:y1 + 1, x0:x1 + 1]] = (65, 65, 65)
    review[daba[y0:y1 + 1, x0:x1 + 1]] = (105, 105, 105)
    review[cleaned[y0:y1 + 1, x0:x1 + 1] & ~(minshan[y0:y1 + 1, x0:x1 + 1] | daba[y0:y1 + 1, x0:x1 + 1])] = (185, 185, 185)
    scale = 5
    shown = Image.fromarray(review).resize(
        (review.shape[1] * scale, review.shape[0] * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 510, max(shown.height, 720)), "white")
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 27)
    body = ImageFont.truetype(font_path, 18)
    small = ImageFont.truetype(font_path, 15)
    label = ImageFont.truetype(font_path, 15)
    lx = shown.width + 22
    draw.text((lx, 20), "岷山—大巴山战略草案", fill=(20, 20, 20), font=title)
    draw.text((lx, 60), "秦蜀西障与汉中—巴蜀南北屏障", fill=(70, 70, 70), font=small)
    draw.rectangle((lx, 105, lx + 28, 133), fill=(65, 65, 65), outline=(30, 30, 30))
    draw.text((lx + 40, 102), f"岷山：{int(minshan.sum())}像素", fill=(25, 25, 25), font=body)
    draw.rectangle((lx, 151, lx + 28, 179), fill=(105, 105, 105), outline=(30, 30, 30))
    draw.text((lx + 40, 148), f"大巴山：{int(daba.sum())}像素", fill=(25, 25, 25), font=body)
    draw.rectangle((lx, 197, lx + 28, 225), fill=(185, 185, 185), outline=(30, 30, 30))
    draw.text((lx + 40, 194), f"残片整理：{int(cleaned.sum())}像素", fill=(25, 25, 25), font=body)

    passages = [
        ("阴平道", 4420, 827, (215, 75, 35)),
        ("岷江谷地", 4427, 846, (25, 105, 190)),
        ("剑门道", 4462 + DABA_SHIFT_X, 862 + DABA_SHIFT_Y, (25, 145, 75)),
        ("米仓道", 4490 + DABA_SHIFT_X, 873 + DABA_SHIFT_Y, (155, 85, 190)),
        ("荔枝道", 4528 + DABA_SHIFT_X, 875 + DABA_SHIFT_Y, (195, 105, 20)),
    ]
    for name, px, py, colour in passages:
        sx, sy = (px - x0) * scale, (py - y0) * scale
        draw.ellipse((sx - 5, sy - 5, sx + 5, sy + 5), fill=colour, outline="white", width=2)
        draw.text((sx + 7, sy - 12), name, fill=colour, font=label,
                  stroke_width=2, stroke_fill="white")

    draw.text((lx, 270), "大巴山三处山口", fill=(25, 25, 25), font=body)
    draw.text((lx, 310), "• 剑门道：汉中—蜀中主轴", fill=(55, 55, 55), font=small)
    draw.text((lx, 344), "• 米仓道：汉中—巴中支线", fill=(55, 55, 55), font=small)
    draw.text((lx, 378), "• 荔枝道：关中—川东迂回线", fill=(55, 55, 55), font=small)
    draw.text((lx, 435), "四段山体使山口成为必争节点", fill=(55, 55, 55), font=small)
    draw.text((lx, 468), "大巴山西北移4×8像素", fill=(55, 55, 55), font=small)
    draw.text((lx, 501), "西端贴近洮州—天水—宁羌交界", fill=(55, 55, 55), font=small)
    draw.text((lx, 534), "无省份被删除；只整理被切断残片", fill=(55, 55, 55), font=small)
    draw.text((lx, 591), "仅输出预览，未写入正式地图", fill=(65, 65, 65), font=small)
    canvas.save(OUT / "minshan_daba_strategy_annotated.png")

    changed = np.any(draft != target, axis=2)
    print(f"MINSHAN_DABA_DRAFT; MINSHAN:{int(minshan.sum())}; DABA:{int(daba.sum())}; CLEANUP:{int(cleaned.sum())}; CHANGED:{int(changed.sum())}")


if __name__ == "__main__":
    main()
