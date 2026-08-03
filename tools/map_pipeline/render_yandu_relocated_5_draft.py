#!/usr/bin/env python3
"""Relocate/refine Yandu around the large Hejian province and reshape its border."""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "guangdong_independent_practice/map/provinces.bmp"
GEOJSON = ROOT / "planning/beijing/110000_full.json"
OUT = ROOT / "planning/beijing"
OLD_HEJIAN = (205, 90, 79)

GROUPS = [
    ("昌平", {"延庆区", "昌平区", "海淀区"}, (36, 183, 73)),
    ("密云", {"怀柔区", "密云区", "平谷区", "顺义区"}, (210, 64, 142)),
    ("燕", {"东城区", "西城区", "朝阳区", "丰台区", "石景山区"}, (89, 177, 232)),
    ("通州", {"通州区", "大兴区"}, (241, 116, 35)),
    ("涿州", {"门头沟区", "房山区"}, (132, 74, 218)),
]

# GeoJSON is projected here only to guide internal placement. The actual outer
# border is a hand-shaped mountain basin following the Yanshan–Taihang arc.
TARGET_BOX = (4598, 692, 4652, 747)  # left, top, right, bottom (inclusive)
MOUNTAIN_BORDER = [
    (4611, 704), (4615, 699), (4623, 695), (4631, 696),
    (4638, 699), (4643, 704), (4647, 710), (4646, 717),
    (4650, 724), (4648, 731), (4644, 737), (4638, 742),
    (4630, 745), (4622, 742), (4614, 743), (4607, 738),
    (4605, 731), (4602, 724), (4604, 716), (4607, 709),
]


def rings(geometry):
    if geometry["type"] == "Polygon":
        yield from geometry["coordinates"]
    else:
        for polygon in geometry["coordinates"]:
            yield from polygon


def nearest_fill(values, valid, target):
    """Fill target pixels from the nearest valid pixel's value (small local grids)."""
    result = values.copy()
    vy, vx = np.nonzero(valid)
    ty, tx = np.nonzero(target)
    for y, x in zip(ty, tx):
        i = np.argmin((vx - x) ** 2 + (vy - y) ** 2)
        result[y, x] = values[vy[i], vx[i]]
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = np.asarray(Image.open(SOURCE).convert("RGB"))
    old_mask = np.all(source == OLD_HEJIAN, axis=2)
    data = json.loads(GEOJSON.read_text())

    points = [p for feature in data["features"] for ring in rings(feature["geometry"]) for p in ring]
    min_lon, max_lon = min(p[0] for p in points), max(p[0] for p in points)
    min_lat, max_lat = min(p[1] for p in points), max(p[1] for p in points)
    left, top, right, bottom = TARGET_BOX

    zones_img = Image.new("I", (source.shape[1], source.shape[0]), 0)
    draw_zones = ImageDraw.Draw(zones_img)
    zone_to_group = {}
    for zone, feature in enumerate(data["features"], start=1):
        name = feature["properties"]["name"]
        group = next(i for i, (_, members, _) in enumerate(GROUPS) if name in members)
        zone_to_group[zone] = group
        for ring in rings(feature["geometry"]):
            polygon = [
                (left + (p[0] - min_lon) / (max_lon - min_lon) * (right - left),
                 top + (max_lat - p[1]) / (max_lat - min_lat) * (bottom - top))
                for p in ring
            ]
            draw_zones.polygon(polygon, fill=zone)
    zones = np.asarray(zones_img)
    border_img = Image.new("1", (source.shape[1], source.shape[0]), 0)
    ImageDraw.Draw(border_img).polygon(MOUNTAIN_BORDER, fill=1)
    target_mask = np.asarray(border_img, dtype=bool)
    owner = np.full(zones.shape, -1, dtype=np.int16)
    for zone, group in zone_to_group.items():
        owner[zones == zone] = group

    # Raster rounding can leave one-pixel holes. Assign them to the nearest
    # already labelled district while retaining the GeoJSON external shape.
    owner[~target_mask] = -1
    holes = target_mask & (owner < 0)
    if holes.any():
        owner = nearest_fill(owner, owner >= 0, holes)

    draft = source.copy()
    removed = old_mask & ~target_mask
    # Return trimmed parts of old Hejian to their nearest surrounding province.
    local_y0, local_y1 = max(0, top - 12), min(source.shape[0], bottom + 13)
    local_x0, local_x1 = max(0, left - 12), min(source.shape[1], right + 13)
    local_src = source[local_y0:local_y1, local_x0:local_x1]
    local_old = old_mask[local_y0:local_y1, local_x0:local_x1]
    local_removed = removed[local_y0:local_y1, local_x0:local_x1]
    restored = nearest_fill(local_src, ~local_old, local_removed)
    draft[local_y0:local_y1, local_x0:local_x1][local_removed] = restored[local_removed]

    for group, (_, _, color) in enumerate(GROUPS):
        draft[target_mask & (owner == group)] = color

    Image.fromarray(draft).save(OUT / "yandu_mountain_border_5_full_draft.bmp")
    pad = 8
    cx0, cy0, cx1, cy1 = left - pad, top - pad, right + pad, bottom + pad
    crop = draft[cy0:cy1 + 1, cx0:cx1 + 1]
    Image.fromarray(crop).save(OUT / "yandu_mountain_border_5_draft.bmp")
    scale = 11
    raw = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    raw.save(OUT / "yandu_mountain_border_5_raw.png")

    local_target = target_mask[cy0:cy1 + 1, cx0:cx1 + 1]
    boundary = np.zeros(local_target.shape, dtype=bool)
    boundary[1:] |= local_target[1:] & np.any(crop[1:] != crop[:-1], axis=2)
    boundary[:, 1:] |= local_target[:, 1:] & np.any(crop[:, 1:] != crop[:, :-1], axis=2)
    shown = np.asarray(raw).copy()
    shown[np.repeat(np.repeat(boundary, scale, 0), scale, 1)] = (35, 35, 35)
    map_img = Image.fromarray(shown)

    canvas = Image.new("RGB", (map_img.width + 410, max(map_img.height, 760)), "white")
    canvas.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 22)
    small = ImageFont.truetype(font_path, 17)
    number_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 18)
    lx = map_img.width + 24
    draw.text((lx, 24), "燕都五省：山川边界版", fill=(20, 20, 20), font=title)
    draw.text((lx, 66), "燕山北界、太行西界；GeoJSON 仅引导内部", fill=(75, 75, 75), font=small)
    for i, (name, _, color) in enumerate(GROUPS, start=1):
        ty = 120 + (i - 1) * 60
        draw.rectangle((lx, ty + 3, lx + 30, ty + 33), fill=color, outline=(35, 35, 35))
        draw.text((lx + 44, ty), f"{i:02d}  {name}", fill=(20, 20, 20), font=body)
        yy, xx = np.nonzero(target_mask & (owner == i - 1))
        sx, sy = int(np.median(xx)), int(np.median(yy))
        px, py = (sx - cx0) * scale, (sy - cy0) * scale
        draw.text((px, py), str(i), fill="black", font=number_font, stroke_width=3, stroke_fill="white")
    borrowed = int(np.count_nonzero(target_mask & ~old_mask))
    returned = int(np.count_nonzero(old_mask & ~target_mask))
    draw.text((lx, 455), "区域名：燕都", fill=(35, 35, 35), font=body)
    draw.text((lx, 505), f"向邻省调整：纳入 {borrowed} / 归还 {returned} 像素", fill=(70, 70, 70), font=small)
    draw.text((lx, 535), "未写入正式 provinces.bmp", fill=(70, 70, 70), font=small)
    canvas.save(OUT / "yandu_mountain_border_5_annotated.png")
    print(f"YANDU_MOUNTAIN_BORDER:5; BORROWED:{borrowed}; RETURNED:{returned}")


if __name__ == "__main__":
    main()
