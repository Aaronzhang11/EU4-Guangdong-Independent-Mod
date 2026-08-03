#!/usr/bin/env python3
"""Render a review-only 14-province Guangxi draft from workshop geometry."""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
SOURCE = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
OUT = ROOT / "planning/guangxi"
OFFSET_X, OFFSET_Y = 422, 29
CURRENT_IDS = [2162, 2164, 4954, 4960, 664, 1840, 2163, 4959]

# Source id, Chinese name, area. Two additional cells are carved below.
SOURCE_PROVINCES = [
    (1840, "桂林", "桂北"), (2163, "柳州", "桂北"), (5355, "平乐", "桂北"),
    (5361, "庆远", "桂东"), (5358, "思恩", "桂东"), (2162, "梧州", "桂东"),
    (5356, "浔州", "桂东"), (5357, "鬱州", "桂东"),
    (2164, "南宁", "桂西"), (664, "泗城", "桂西"), (5360, "镇安", "桂西"),
    (5359, "思明", "桂西"),
]
PROVINCES = [(name, area) for _, name, area in SOURCE_PROVINCES] + [("全州", "桂北"), ("田州", "桂西")]


def definitions(path: Path):
    result = {}
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if len(fields) >= 5 and fields[0].isdigit():
            result[int(fields[0])] = tuple(map(int, fields[1:4]))
    return result


def packed_mask(bitmap, colours):
    packed = ((bitmap[:, :, 0].astype(np.uint32) << 16)
              | (bitmap[:, :, 1].astype(np.uint32) << 8)
              | bitmap[:, :, 2].astype(np.uint32))
    keys = np.array([(r << 16) | (g << 8) | b for r, g, b in colours], dtype=np.uint32)
    return np.isin(packed, keys)


def split_connected(mask, first_seed, second_seed):
    """Two-source four-way growth keeps both daughter provinces connected."""
    owner = np.full(mask.shape, -1, dtype=np.int16)
    queue = deque()
    yy, xx = np.where(mask)
    for label, (sx, sy) in enumerate((first_seed, second_seed)):
        pos = np.argmin((xx - sx) ** 2 + (yy - sy) ** 2)
        x, y = int(xx[pos]), int(yy[pos])
        owner[y, x] = label
        queue.append((x, y, label))
    while queue:
        x, y, label = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0]
                    and mask[ny, nx] and owner[ny, nx] < 0):
                owner[ny, nx] = label
                queue.append((nx, ny, label))
    return owner


def font(size):
    for path in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    current = np.asarray(Image.open(MOD / "map/provinces.bmp").convert("RGB"))
    source = np.asarray(Image.open(SOURCE / "map/provinces.bmp").convert("RGB"))
    current_defs = definitions(MOD / "map/definition.csv")
    source_defs = definitions(SOURCE / "map/definition.csv")
    original = packed_mask(current, [current_defs[i] for i in CURRENT_IDS])

    labels = np.full(original.shape, -1, dtype=np.int16)
    colours = []
    for index, (pid, _name, _area) in enumerate(SOURCE_PROVINCES):
        colour = source_defs[pid]
        colours.append(colour)
        sy, sx = np.where(np.all(source == colour, axis=2))
        ty, tx = sy - OFFSET_Y, sx - OFFSET_X
        valid = (tx >= 0) & (tx < current.shape[1]) & (ty >= 0) & (ty < current.shape[0])
        labels[ty[valid], tx[valid]] = index

    # Split workshop Guilin northward into Guilin and Quanzhou.
    guilin_i = next(i for i, (_, n, _) in enumerate(SOURCE_PROVINCES) if n == "桂林")
    guilin_mask = labels == guilin_i
    split = split_connected(guilin_mask, (4532, 986), (4540, 968))
    labels[guilin_mask & (split == 0)] = guilin_i
    labels[guilin_mask & (split == 1)] = 12

    # Split the large western Sicheng cell into Sicheng and Tianzhou.
    sicheng_i = next(i for i, (_, n, _) in enumerate(SOURCE_PROVINCES) if n == "泗城")
    sicheng_mask = labels == sicheng_i
    split = split_connected(sicheng_mask, (4442, 988), (4466, 1001))
    labels[sicheng_mask & (split == 0)] = sicheng_i
    labels[sicheng_mask & (split == 1)] = 13

    # The source mod's Guangxi outer mask overlaps this project's Guizhou,
    # Guangdong and Annam. Keep only its internal geometry and lock the current
    # Guangxi outline so formal application cannot retire neighbouring provinces.
    labels[~original] = -1

    # Review-only unique colours for Quanzhou and Tianzhou.
    colours += [(227, 142, 44), (69, 166, 112)]

    # Retain the current Guangxi outer extent wherever the workshop mask is smaller.
    assigned = labels >= 0
    queue = deque((int(x), int(y)) for y, x in zip(*np.where(assigned & original)))
    filled = assigned.copy()
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < original.shape[1] and 0 <= ny < original.shape[0]
                    and original[ny, nx] and not filled[ny, nx]):
                labels[ny, nx] = labels[y, x]
                filled[ny, nx] = True
                queue.append((nx, ny))
    if np.any(original & ~filled):
        raise ValueError("Could not fill current Guangxi outline")

    draft = current.copy()
    for i, colour in enumerate(colours):
        draft[labels == i] = colour
    changed = np.any(draft != current, axis=2)
    Image.fromarray(draft).save(OUT / "guangxi_workshop_14_full_draft.bmp", format="BMP")

    scope = original
    yy, xx = np.where(scope)
    pad = 7
    x0, x1 = max(0, xx.min() - pad), min(current.shape[1], xx.max() + pad + 1)
    y0, y1 = max(0, yy.min() - pad), min(current.shape[0], yy.max() + pad + 1)
    crop = draft[y0:y1, x0:x1]
    Image.fromarray(crop).save(OUT / "guangxi_workshop_14_draft.bmp", format="BMP")
    scale = 7
    raw = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    raw.save(OUT / "guangxi_workshop_14_raw.png")

    local_scope = scope[y0:y1, x0:x1]
    boundary = np.zeros(local_scope.shape, dtype=bool)
    boundary[1:] |= local_scope[1:] & np.any(crop[1:] != crop[:-1], axis=2)
    boundary[:, 1:] |= local_scope[:, 1:] & np.any(crop[:, 1:] != crop[:, :-1], axis=2)
    shown = np.asarray(raw).copy()
    shown[np.repeat(np.repeat(boundary, scale, 0), scale, 1)] = (35, 35, 35)
    map_img = Image.fromarray(shown)

    sidebar = 540
    canvas = Image.new("RGB", (map_img.width + sidebar, max(map_img.height, 760)), (248, 247, 243))
    canvas.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    title, body, small = font(29), font(19), font(15)
    lx = map_img.width + 24
    draw.text((lx, 20), "广西十四省 · 大明日不落几何草案", fill=(22, 22, 22), font=title)
    draw.text((lx, 60), "十二省原界移植；桂林拆全州，泗城拆田州", fill=(75, 75, 75), font=small)

    area_order = ["桂北", "桂东", "桂西"]
    order = [i for area in area_order for i, (_, a) in enumerate(PROVINCES) if a == area]
    for pos, i in enumerate(order):
        name, area = PROVINCES[i]
        col, row = pos // 7, pos % 7
        tx, ty = lx + col * 250, 105 + row * 52
        draw.rectangle((tx, ty + 3, tx + 23, ty + 26), fill=colours[i], outline=(40, 40, 40))
        draw.text((tx + 32, ty), f"{i + 1:02d} {name} · {area}", fill=(30, 30, 30), font=body)
        py, px = np.where(labels == i)
        if len(px):
            cx, cy = int((np.median(px) - x0) * scale), int((np.median(py) - y0) * scale)
            draw.text((cx, cy), str(i + 1), anchor="mm", fill=(15, 15, 15),
                      stroke_width=3, stroke_fill=(255, 255, 255), font=body)

    draw.text((lx, 500), "桂北4省 · 桂东5省 · 桂西5省", fill=(50, 50, 50), font=body)
    draw.text((lx, 540), "现有广西外框锁定；原模组仅引导内部省界", fill=(75, 75, 75), font=small)
    draw.text((lx, 568), "仅为预览，未写入正式 provinces.bmp", fill=(75, 75, 75), font=small)
    canvas.save(OUT / "guangxi_workshop_14_annotated.png")

    sizes = {PROVINCES[i][0]: int(np.count_nonzero(labels == i)) for i in range(14)}
    print(f"GUANGXI_DRAFT; PROVINCES:14; CHANGED:{int(changed.sum())}; SIZES:{sizes}")


if __name__ == "__main__":
    main()
