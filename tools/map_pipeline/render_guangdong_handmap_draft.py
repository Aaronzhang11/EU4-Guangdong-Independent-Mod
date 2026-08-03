#!/usr/bin/env python3
"""Render a Guangdong-only province draft without changing the canonical map."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "guangdong_independent_practice/map/provinces.bmp"
OUT_DIR = ROOT / "planning/guangdong"

# Only these current mainland province colours may be repartitioned. Hainan is
# deliberately absent. Dongguan, Hong Kong and Macau are restored afterwards.
MAINLAND_COLOURS = {
    (223, 82, 0), (223, 86, 128), (95, 88, 192), (146, 81, 81),
    (65, 52, 224), (65, 46, 176), (64, 44, 160), (64, 32, 64),
    (190, 91, 45), (67, 219, 159), (187, 30, 204), (186, 212, 73),
    (20, 200, 220), (106, 60, 226), (190, 128, 45), (67, 219, 198),
}
LOCKED = {
    "东莞": (67, 219, 159),
    "香港": (20, 200, 220),
    "澳门": (95, 88, 192),
}

# Seeds follow the relative placement in the supplied hand-drawn reference.
# Coordinates are in the current 5632x2048 province bitmap.
SEEDS = [
    ("连州", 4555, 989), ("韶州", 4575, 991), ("南雄", 4591, 987),
    ("英德", 4569, 1001), ("清远", 4574, 1008), ("四会", 4560, 1012),
    ("德庆", 4548, 1014), ("肇庆", 4565, 1019), ("罗定", 4545, 1025),
    ("云浮", 4555, 1026), ("高州", 4536, 1040), ("化州", 4525, 1040),
    ("廉州", 4505, 1041), ("雷州", 4525, 1063), ("阳江", 4548, 1046),
    ("恩平", 4558, 1037), ("新会", 4569, 1038),
    ("广州", 4578, 1020), ("佛山", 4570, 1026), ("顺德", 4575, 1031),
    ("香山", 4579, 1037), ("新安", 4592, 1031),
    ("惠州", 4596, 1017), ("归善", 4604, 1022), ("海丰", 4613, 1026),
    ("河源", 4603, 1005), ("龙川", 4612, 998), ("嘉应", 4620, 997),
    ("潮州", 4628, 1007), ("揭阳", 4627, 1018),
]

PALETTE = [
    (205, 78, 72), (78, 121, 189), (106, 168, 79), (184, 116, 55),
    (128, 95, 170), (57, 157, 176), (218, 133, 166), (144, 123, 92),
    (231, 178, 53), (90, 174, 136), (200, 92, 129), (102, 105, 196),
    (210, 132, 78), (74, 143, 113), (171, 82, 193), (49, 159, 205),
    (222, 101, 91), (115, 153, 52), (183, 139, 204), (53, 117, 156),
    (231, 155, 37), (88, 178, 187), (166, 91, 94), (118, 131, 55),
    (211, 99, 180), (57, 98, 204), (190, 151, 68), (89, 151, 95),
    (148, 84, 145), (46, 145, 162),
]


def colour_mask(arr: np.ndarray, colours: set[tuple[int, int, int]]) -> np.ndarray:
    packed = (arr[:, :, 0].astype(np.uint32) << 16) | (arr[:, :, 1].astype(np.uint32) << 8) | arr[:, :, 2]
    keys = np.array([(r << 16) | (g << 8) | b for r, g, b in colours], dtype=np.uint32)
    return np.isin(packed, keys)


def nearest_mask_pixel(mask: np.ndarray, x: int, y: int) -> tuple[int, int]:
    if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1] and mask[y, x]:
        return x, y
    yy, xx = np.nonzero(mask)
    i = np.argmin((xx - x) ** 2 + (yy - y) ** 2)
    return int(xx[i]), int(yy[i])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = np.asarray(Image.open(SOURCE).convert("RGB"))
    mainland = colour_mask(source, MAINLAND_COLOURS)
    lock_masks = {name: colour_mask(source, {rgb}) for name, rgb in LOCKED.items()}
    editable = mainland.copy()
    for mask in lock_masks.values():
        editable &= ~mask

    yy, xx = np.nonzero(editable)
    assigned = np.empty(len(xx), dtype=np.int16)
    best = np.full(len(xx), np.inf)
    snapped = []
    for i, (name, sx, sy) in enumerate(SEEDS):
        sx, sy = nearest_mask_pixel(editable, sx, sy)
        snapped.append((name, sx, sy))
        # Slight east-west preference produces less strip-like regions on this tiny map.
        dist = ((xx - sx) / 1.10) ** 2 + ((yy - sy) / 0.92) ** 2
        take = dist < best
        assigned[take] = i
        best[take] = dist[take]

    draft = source.copy()
    for i, colour in enumerate(PALETTE[:len(SEEDS)]):
        hit = assigned == i
        draft[yy[hit], xx[hit]] = colour
    for name, mask in lock_masks.items():
        draft[mask] = LOCKED[name]

    # Hard safety assertions: the external silhouette and the locked provinces are exact.
    assert np.array_equal(draft[~mainland], source[~mainland])
    for mask in lock_masks.values():
        assert np.array_equal(draft[mask], source[mask])

    full_path = OUT_DIR / "guangdong_handmap_internal_full_draft.bmp"
    Image.fromarray(draft).save(full_path)

    y0, x0 = np.min(np.argwhere(mainland), axis=0)
    y1, x1 = np.max(np.argwhere(mainland), axis=0)
    pad = 5
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(draft.shape[1] - 1, x1 + pad), min(draft.shape[0] - 1, y1 + pad)
    crop = draft[y0:y1 + 1, x0:x1 + 1]
    Image.fromarray(crop).save(OUT_DIR / "guangdong_handmap_internal_draft.bmp")

    scale = 10
    raw = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    raw.save(OUT_DIR / "guangdong_handmap_internal_raw.png")

    # Add crisp province outlines and a numbered legend so crowded Pearl River Delta
    # names remain readable without altering the BMP itself.
    local = draft[y0:y1 + 1, x0:x1 + 1]
    boundary = np.zeros(local.shape[:2], dtype=bool)
    boundary[1:, :] |= np.any(local[1:, :] != local[:-1, :], axis=2)
    boundary[:, 1:] |= np.any(local[:, 1:] != local[:, :-1], axis=2)
    preview = np.asarray(raw).copy()
    big_boundary = np.repeat(np.repeat(boundary, scale, axis=0), scale, axis=1)
    preview[big_boundary] = (35, 35, 35)
    map_img = Image.fromarray(preview)

    legend_w = 430
    canvas = Image.new("RGB", (map_img.width + legend_w, max(map_img.height, 820)), "white")
    canvas.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title_font = ImageFont.truetype(font_path, 27)
    font = ImageFont.truetype(font_path, 20)
    small = ImageFont.truetype(font_path, 16)
    lx = map_img.width + 24
    draw.text((lx, 20), "广东细化草案（手绘图方案）", fill=(20, 20, 20), font=title_font)
    draw.text((lx, 58), "外边界锁定；仅重分广东内部像素", fill=(85, 85, 85), font=small)
    entries = [(n, PALETTE[i]) for i, (n, _, _) in enumerate(snapped)] + list(LOCKED.items())
    for i, (name, colour) in enumerate(entries):
        col = i // 17
        row = i % 17
        tx = lx + col * 195
        ty = 100 + row * 38
        draw.rectangle((tx, ty + 3, tx + 24, ty + 27), fill=colour, outline=(40, 40, 40))
        draw.text((tx + 34, ty), f"{i + 1:02d}  {name}", fill=(25, 25, 25), font=font)

    # Number each province close to its seed. Locked units use their actual centroids.
    number_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 17)
    for i, (_, sx, sy) in enumerate(snapped):
        px, py = (sx - x0) * scale + 2, (sy - y0) * scale - 3
        label = str(i + 1)
        box = draw.textbbox((px, py), label, font=number_font, stroke_width=2)
        draw.rectangle((box[0] - 2, box[1] - 1, box[2] + 2, box[3] + 1), fill=(255, 255, 255))
        draw.text((px, py), label, fill=(0, 0, 0), font=number_font)
    for j, (name, mask) in enumerate(lock_masks.items(), start=len(snapped) + 1):
        ly, lx0 = np.nonzero(mask)
        sx, sy = int(np.mean(lx0)), int(np.mean(ly))
        px, py = (sx - x0) * scale + 2, (sy - y0) * scale - 3
        draw.text((px, py), str(j), fill=(0, 0, 0), font=number_font, stroke_width=3, stroke_fill="white")

    draw.text((lx, 765), "保留：东莞、香港、澳门原像素", fill=(60, 60, 60), font=small)
    draw.text((lx, 790), "未写入正式 provinces.bmp", fill=(60, 60, 60), font=small)
    canvas.save(OUT_DIR / "guangdong_handmap_internal_annotated.png")

    changed_outside = int(np.count_nonzero(np.any(draft[~mainland] != source[~mainland], axis=1)))
    print(f"mainland pixels: {int(mainland.sum())}")
    print(f"draft units: {len(entries)}")
    print(f"changed pixels outside Guangdong: {changed_outside}")
    print(f"crop: {x0},{y0}..{x1},{y1}")


if __name__ == "__main__":
    main()
