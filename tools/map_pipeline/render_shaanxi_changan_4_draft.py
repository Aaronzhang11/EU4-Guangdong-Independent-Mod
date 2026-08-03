#!/usr/bin/env python3
"""Split the workshop Xi'an province into a four-province Chang'an area."""

from __future__ import annotations

from collections import Counter
import heapq
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render_workshop_shaanxi_draft as base


OUT = base.OUT
SOURCE_FULL = OUT / "shaanxi_workshop_20_full_draft.bmp"

# Name, historical orientation, target size, preview colour.
PROVINCES = [
    ("咸阳", (4501, 824), 68, (210, 73, 128)),
    ("镐京", (4498, 833), 56, (226, 157, 42)),
    ("长安", (4510, 829), 76, (74, 157, 215)),
    ("蓝田", (4517, 835), 48, (78, 179, 91)),
]


def snap(mask, x, y):
    yy, xx = np.nonzero(mask)
    i = int(np.argmin((xx - x) ** 2 + (yy - y) ** 2))
    return int(xx[i]), int(yy[i])


def grow_balanced(mask, seeds, quotas):
    """Round-robin compact growth gives four exact, connected jurisdictions."""
    owner = np.full(mask.shape, -1, dtype=np.int16)
    frontiers, queued, counts = {}, {}, Counter()
    for province, (sx, sy) in enumerate(seeds):
        owner[sy, sx] = province
        counts[province] = 1
        frontiers[province] = []
        queued[province] = np.zeros(mask.shape, dtype=bool)

    def add(province, x, y):
        sx, sy = seeds[province]
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0]
                    and mask[ny, nx] and owner[ny, nx] < 0 and not queued[province][ny, nx]):
                queued[province][ny, nx] = True
                compact = (nx - sx) ** 2 + (ny - sy) ** 2
                heapq.heappush(frontiers[province], (compact, nx, ny))

    for province, (sx, sy) in enumerate(seeds):
        add(province, sx, sy)
    while any(counts[p] < quotas[p] for p in range(len(seeds))):
        progressed = False
        for province in range(len(seeds)):
            if counts[province] >= quotas[province]:
                continue
            queue = frontiers[province]
            while queue and owner[queue[0][2], queue[0][1]] >= 0:
                heapq.heappop(queue)
            if not queue:
                continue
            _, x, y = heapq.heappop(queue)
            owner[y, x] = province
            counts[province] += 1
            add(province, x, y)
            progressed = True
        if not progressed:
            raise ValueError(f"Chang'an growth stopped early: {dict(counts)}")
    return owner


def main():
    if not SOURCE_FULL.exists():
        base.main()
    draft = np.asarray(Image.open(SOURCE_FULL).convert("RGB")).copy()
    source = np.asarray(Image.open(base.SOURCE_MAP / "provinces.bmp").convert("RGB"))
    source_defs = base.definitions(base.SOURCE_MAP / "definition.csv")
    translated = source[
        base.SOURCE_Y_OFFSET:base.SOURCE_Y_OFFSET + draft.shape[0],
        base.SOURCE_X_OFFSET:base.SOURCE_X_OFFSET + draft.shape[1],
    ]
    xian_mask = np.all(translated == source_defs[700][0], axis=2)
    if int(xian_mask.sum()) != sum(p[2] for p in PROVINCES):
        raise ValueError("Unexpected Xi'an source size")

    seeds = [snap(xian_mask, *province[1]) for province in PROVINCES]
    owner = grow_balanced(xian_mask, seeds, [province[2] for province in PROVINCES])
    for province, (_, _, _, colour) in enumerate(PROVINCES):
        draft[owner == province] = colour

    Image.fromarray(draft).save(OUT / "shaanxi_changan_4_full_draft.bmp")

    # Keep an ordinary provinces.bmp-style Shaanxi crop for inspection.
    mountain_mask = base.mask_for(translated, [source_defs[p][0] for p in base.MOUNTAINS])
    shaanxi_mask = base.mask_for(translated, [source_defs[p][0] for p in base.PROVINCE_IDS])
    yy, xx = np.nonzero(shaanxi_mask | mountain_mask)
    pad = 8
    x0, x1 = int(xx.min()) - pad, int(xx.max()) + pad
    y0, y1 = int(yy.min()) - pad, int(yy.max()) + pad
    crop = draft[y0:y1 + 1, x0:x1 + 1]
    Image.fromarray(crop).save(OUT / "shaanxi_changan_4_draft.bmp")

    # Focused annotated review around the Wei valley and northern Qinling.
    fx0, fx1, fy0, fy1 = 4478, 4543, 798, 856
    focus = draft[fy0:fy1 + 1, fx0:fx1 + 1].copy()
    local_translated = translated[fy0:fy1 + 1, fx0:fx1 + 1]
    for pid in base.MOUNTAINS:
        grey = (72, 72, 72) if pid == 5183 else (128, 128, 128)
        focus[np.all(local_translated == source_defs[pid][0], axis=2)] = grey
    scale = 12
    shown = Image.fromarray(focus).resize(
        (focus.shape[1] * scale, focus.shape[0] * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 360, max(shown.height, 710)), "white")
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 20)
    small = ImageFont.truetype(font_path, 16)
    lx = shown.width + 22
    draw.text((lx, 20), "长安四省草案", fill=(20, 20, 20), font=title)
    draw.text((lx, 62), "渭河京畿；南倚秦岭", fill=(75, 75, 75), font=small)
    for i, (name, _, quota, colour) in enumerate(PROVINCES):
        y = 112 + i * 62
        draw.rectangle((lx, y + 2, lx + 30, y + 32), fill=colour, outline=(30, 30, 30))
        draw.text((lx + 42, y), f"{i + 1:02d} {name}（{quota}像素）", fill=(25, 25, 25), font=body)
        sx, sy = seeds[i]
        draw.text(((sx - fx0) * scale, (sy - fy0) * scale), str(i + 1),
                  fill="black", font=body, stroke_width=3, stroke_fill="white")
    draw.rectangle((lx, 390, lx + 30, 420), fill=(72, 72, 72), outline=(30, 30, 30))
    draw.text((lx + 42, 388), "秦岭（不可通行）", fill=(25, 25, 25), font=body)
    draw.text((lx, 455), "区域：长安", fill=(45, 45, 45), font=body)
    draw.text((lx, 500), "咸阳居渭北；镐京在西南", fill=(65, 65, 65), font=small)
    draw.text((lx, 530), "长安居中；蓝田扼东南山口", fill=(65, 65, 65), font=small)
    draw.text((lx, 585), "未写入正式 provinces.bmp", fill=(65, 65, 65), font=small)
    canvas.save(OUT / "shaanxi_changan_4_annotated.png")
    print("SHAANXI_CHANGAN_DRAFT:4; PIXELS:248; FORMAL_UNCHANGED:1")


if __name__ == "__main__":
    main()
