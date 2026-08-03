#!/usr/bin/env python3
"""Render the source-mod Minshan using a minimum-change overlay."""

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
OUT = ROOT / "planning/minshan"
MINSHAN_ID = 5176
MINSHAN_COLOUR = (166, 234, 140)
SOURCE_X_OFFSET = 423
SOURCE_Y_OFFSET = 11


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    target = np.asarray(Image.open(TARGET_MAP / "provinces.bmp").convert("RGB"))
    source = np.asarray(Image.open(SOURCE_MAP / "provinces.bmp").convert("RGB"))
    source_defs, _ = common.read_definitions(SOURCE_MAP / "definition.csv")
    translated = source[
        SOURCE_Y_OFFSET:SOURCE_Y_OFFSET + target.shape[0],
        SOURCE_X_OFFSET:SOURCE_X_OFFSET + target.shape[1],
    ]
    mountain = np.all(translated == source_defs[MINSHAN_ID][0], axis=2)
    if int(mountain.sum()) != 607:
        raise ValueError("Unexpected Minshan source size")

    draft = target.copy()
    affected_colours = np.unique(target[mountain].reshape(-1, 3), axis=0)
    draft[mountain] = MINSHAN_COLOUR
    cleaned = np.zeros(mountain.shape, dtype=bool)

    # Retain the largest body of each donor province. Tiny pieces cut off by
    # the ridge are absorbed into the province/mountain sharing most edges.
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

    Image.fromarray(draft).save(OUT / "minshan_minimal_full_draft.bmp")
    x0, x1, y0, y1 = 4388, 4480, 795, 900
    crop = draft[y0:y1 + 1, x0:x1 + 1]
    Image.fromarray(crop).save(OUT / "minshan_minimal_draft.bmp")

    review = crop.copy()
    local_mountain = mountain[y0:y1 + 1, x0:x1 + 1]
    local_cleaned = cleaned[y0:y1 + 1, x0:x1 + 1]
    review[local_mountain] = (72, 72, 72)
    review[local_cleaned & ~local_mountain] = (185, 185, 185)
    scale = 7
    shown = Image.fromarray(review).resize(
        (review.shape[1] * scale, review.shape[0] * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 490, max(shown.height, 760)), "white")
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 27)
    body = ImageFont.truetype(font_path, 18)
    small = ImageFont.truetype(font_path, 15)
    map_label = ImageFont.truetype(font_path, 16)
    lx = shown.width + 22
    draw.text((lx, 20), "岷山最小改动草案", fill=(20, 20, 20), font=title)
    draw.text((lx, 60), "原山体607像素；四段结构不缩放", fill=(70, 70, 70), font=small)
    draw.rectangle((lx, 108, lx + 28, 136), fill=(72, 72, 72), outline=(30, 30, 30))
    draw.text((lx + 40, 105), "岷山（不可通行）", fill=(25, 25, 25), font=body)
    draw.rectangle((lx, 154, lx + 28, 182), fill=(185, 185, 185), outline=(30, 30, 30))
    draw.text((lx + 40, 151), f"残片整理（{int(cleaned.sum())}像素）", fill=(25, 25, 25), font=body)

    passages = [
        ("阴平道", (4420, 827), (225, 85, 35)),
        ("岷江谷地", (4427, 846), (30, 105, 190)),
        ("剑门道", (4459, 861), (30, 145, 75)),
    ]
    for name, (px, py), colour in passages:
        sx, sy = (px - x0) * scale, (py - y0) * scale
        draw.ellipse((sx - 5, sy - 5, sx + 5, sy + 5), fill=colour, outline="white", width=2)
        draw.text((sx + 8, sy - 13), name, fill=colour, font=map_label,
                  stroke_width=2, stroke_fill="white")

    draw.text((lx, 230), "战略通道", fill=(25, 25, 25), font=body)
    draw.text((lx, 270), "• 剑门道：汉中—蜀中主轴", fill=(55, 55, 55), font=small)
    draw.text((lx, 304), "• 阴平道：陇南奇袭路线", fill=(55, 55, 55), font=small)
    draw.text((lx, 338), "• 岷江谷地：茂州—成都通道", fill=(55, 55, 55), font=small)
    draw.text((lx, 405), "受影响较多：洮州、若尔盖、阿坝", fill=(55, 55, 55), font=small)
    draw.text((lx, 438), "没有省份被删除；外部地图保持不变", fill=(55, 55, 55), font=small)
    draw.text((lx, 495), "仅输出预览，未写入正式地图", fill=(65, 65, 65), font=small)
    canvas.save(OUT / "minshan_minimal_annotated.png")

    changed = np.any(draft != target, axis=2)
    print(f"MINSHAN_MINIMAL_DRAFT:607; CLEANUP:{int(cleaned.sum())}; CHANGED:{int(changed.sum())}")


if __name__ == "__main__":
    main()
