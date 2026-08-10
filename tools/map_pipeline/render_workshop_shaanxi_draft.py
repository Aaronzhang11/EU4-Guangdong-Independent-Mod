#!/usr/bin/env python3
"""Render a review-only transplant of the workshop mod's Shaanxi."""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
TARGET_MAP = ROOT / "guangdong_independent_practice/map"
SOURCE_MAP = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255/map"
)
OUT = ROOT / "planning/shaanxi"

# Best local overlap of the two Shaanxi outer masks. Like Hebei, this is a
# translation only: province pixels are not resampled.
SOURCE_X_OFFSET = 423
SOURCE_Y_OFFSET = 11

AREAS = {
    "关中": [700, 4198, 5271, 5269, 5270],
    "陕北": [2179, 5268, 5267, 5266, 5265],
    "陕南": [689, 5275, 5274, 5273, 5272],
    "陕西": [2181, 5276, 5277, 5282, 5278],
}
PROVINCE_IDS = [pid for ids in AREAS.values() for pid in ids]
OLD_SHAANXI_IDS = [689, 700, 2179, 4198]

NAMES = {
    700: "西安", 4198: "凤翔", 5271: "彬州", 5269: "同州", 5270: "华州",
    2179: "延安", 5268: "富州", 5267: "绥德", 5266: "榆林", 5265: "葭州",
    689: "汉中", 5275: "宁羌", 5274: "兴安", 5273: "金州", 5272: "商州",
    2181: "平凉", 5276: "秦安", 5277: "固原", 5282: "泾州", 5278: "静宁",
}

# Only impassables touching a Shaanxi province are included. 5183 is Qinling.
MOUNTAINS = {
    5183: "秦岭", 5175: "大巴山", 5176: "岷山", 5182: "伏牛山",
    5180: "中条山", 5187: "陇山",
}


def definitions(path):
    by_id = {}
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if len(fields) >= 5 and fields[0].isdigit():
            by_id[int(fields[0])] = (tuple(map(int, fields[1:4])), fields[4])
    return by_id


def mask_for(bitmap, colours):
    packed = ((bitmap[:, :, 0].astype(np.uint32) << 16)
              | (bitmap[:, :, 1].astype(np.uint32) << 8)
              | bitmap[:, :, 2].astype(np.uint32))
    keys = np.array([(r << 16) | (g << 8) | b for r, g, b in colours], dtype=np.uint32)
    return np.isin(packed, keys)


def fill_retired(bitmap, retired, forbidden):
    colours = np.zeros((*retired.shape, 3), dtype=np.uint8)
    assigned = np.zeros(retired.shape, dtype=bool)
    queue = deque()
    height, width = retired.shape
    for y, x in zip(*np.nonzero(retired)):
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and not forbidden[ny, nx]:
                colours[y, x] = bitmap[ny, nx]
                assigned[y, x] = True
                queue.append((x, y))
                break
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height and retired[ny, nx]
                    and not assigned[ny, nx]):
                assigned[ny, nx] = True
                colours[ny, nx] = colours[y, x]
                queue.append((nx, ny))
    if np.any(retired & ~assigned):
        raise ValueError("Could not return all old Shaanxi pixels to neighbours")
    return colours


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    target = np.asarray(Image.open(TARGET_MAP / "provinces.bmp").convert("RGB"))
    source = np.asarray(Image.open(SOURCE_MAP / "provinces.bmp").convert("RGB"))
    target_defs, source_defs = definitions(TARGET_MAP / "definition.csv"), definitions(SOURCE_MAP / "definition.csv")
    translated = source[
        SOURCE_Y_OFFSET:SOURCE_Y_OFFSET + target.shape[0],
        SOURCE_X_OFFSET:SOURCE_X_OFFSET + target.shape[1],
    ]

    province_mask = mask_for(translated, [source_defs[p][0] for p in PROVINCE_IDS])
    mountain_mask = mask_for(translated, [source_defs[p][0] for p in MOUNTAINS])
    imported_mask = province_mask | mountain_mask
    old_mask = mask_for(target, [target_defs[p][0] for p in OLD_SHAANXI_IDS])

    draft = target.copy()
    retired = old_mask & ~imported_mask
    if np.any(retired):
        returned = fill_retired(target, retired, old_mask | imported_mask)
        draft[retired] = returned[retired]

    for pid in PROVINCE_IDS:
        pixels = np.all(translated == source_defs[pid][0], axis=2)
        draft[pixels] = source_defs[pid][0]
    for pid in MOUNTAINS:
        pixels = np.all(translated == source_defs[pid][0], axis=2)
        draft[pixels] = source_defs[pid][0]

    Image.fromarray(draft).save(OUT / "shaanxi_workshop_20_full_draft.bmp")
    yy, xx = np.nonzero(imported_mask | old_mask)
    pad = 8
    x0, x1 = int(xx.min()) - pad, int(xx.max()) + pad
    y0, y1 = int(yy.min()) - pad, int(yy.max()) + pad
    crop = draft[y0:y1 + 1, x0:x1 + 1]
    Image.fromarray(crop).save(OUT / "shaanxi_workshop_20_draft.bmp")

    # Review render: province colours stay distinct, while all impassables are
    # grey and Qinling is deliberately darkest.
    review = crop.copy()
    local_translated = translated[y0:y1 + 1, x0:x1 + 1]
    for pid in MOUNTAINS:
        grey = (72, 72, 72) if pid == 5183 else (128, 128, 128)
        review[np.all(local_translated == source_defs[pid][0], axis=2)] = grey
    scale = 6
    shown = Image.fromarray(review).resize(
        (review.shape[1] * scale, review.shape[0] * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 510, max(shown.height, 980)), "white")
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 27)
    body = ImageFont.truetype(font_path, 17)
    small = ImageFont.truetype(font_path, 15)
    number = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 15)
    lx = shown.width + 22
    draw.text((lx, 18), "陕西原图移植草案", fill=(20, 20, 20), font=title)
    draw.text((lx, 58), "20省；秦岭及相邻不可通行山系保留", fill=(75, 75, 75), font=small)

    rows = [(pid, area) for area, ids in AREAS.items() for pid in ids]
    for i, (pid, area) in enumerate(rows):
        col, row = i // 10, i % 10
        tx, ty = lx + col * 238, 98 + row * 48
        colour = source_defs[pid][0]
        draw.rectangle((tx, ty + 2, tx + 24, ty + 27), fill=colour, outline=(30, 30, 30))
        draw.text((tx + 33, ty), f"{i + 1:02d} {NAMES[pid]} · {area}", fill=(25, 25, 25), font=body)
        py, px = np.nonzero(np.all(translated == source_defs[pid][0], axis=2))
        sx, sy = float(np.median(px)), float(np.median(py))
        draw.text(((sx - x0) * scale, (sy - y0) * scale), str(i + 1),
                  fill="black", font=number, stroke_width=3, stroke_fill="white")

    draw.rectangle((lx, 615, lx + 25, 640), fill=(72, 72, 72), outline=(30, 30, 30))
    draw.text((lx + 34, 612), "秦岭（不可通行，深灰）", fill=(30, 30, 30), font=body)
    draw.rectangle((lx, 655, lx + 25, 680), fill=(128, 128, 128), outline=(30, 30, 30))
    draw.text((lx + 34, 652), "其他不可通行山地（灰）", fill=(30, 30, 30), font=body)
    draw.text((lx, 705), "大巴山、岷山、伏牛山、中条山、陇山", fill=(55, 55, 55), font=small)
    draw.text((lx, 740), "仅输出预览，未写入正式 provinces.bmp", fill=(55, 55, 55), font=small)
    draw.text((lx, 770), "局部坐标平移：x−423，y−11；未缩放", fill=(55, 55, 55), font=small)
    canvas.save(OUT / "shaanxi_workshop_20_annotated.png")

    changed = np.any(draft != target, axis=2)
    outside = int(np.count_nonzero(changed & ~(old_mask | imported_mask)))
    print(f"SHAANXI_WORKSHOP_DRAFT:20; MOUNTAINS:{len(MOUNTAINS)}; OUTSIDE:{outside}")


if __name__ == "__main__":
    main()
