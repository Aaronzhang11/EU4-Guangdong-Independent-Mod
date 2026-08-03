#!/usr/bin/env python3
"""Render a five-province Yandu preview inside the current Beijing outline."""

import heapq
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "guangdong_independent_practice/map/provinces.bmp"
GEOJSON = ROOT / "planning/beijing/110000_full.json"
OUT = ROOT / "planning/beijing"
BEIJING_COLOR = (227, 142, 0)

PROVINCES = [
    ("昌平", 4622, 743, (78, 121, 189)),
    ("密云", 4637, 742, (106, 168, 79)),
    ("京师", 4628, 754, (201, 79, 74)),
    ("通州", 4638, 760, (55, 157, 176)),
    ("涿州", 4619, 765, (190, 122, 54)),
]


def rings(geometry):
    if geometry["type"] == "Polygon":
        yield from geometry["coordinates"]
    else:
        for polygon in geometry["coordinates"]:
            yield from polygon


def snap(mask, x, y):
    if mask[y, x]:
        return x, y
    yy, xx = np.nonzero(mask)
    i = np.argmin((xx - x) ** 2 + (yy - y) ** 2)
    return int(xx[i]), int(yy[i])


def geo_guide(mask, x0, y0, x1, y1):
    data = json.loads(GEOJSON.read_text())
    points = [p for feature in data["features"] for ring in rings(feature["geometry"]) for p in ring]
    min_lon, max_lon = min(p[0] for p in points), max(p[0] for p in points)
    min_lat, max_lat = min(p[1] for p in points), max(p[1] for p in points)
    image = Image.new("I", (mask.shape[1], mask.shape[0]), 0)
    draw = ImageDraw.Draw(image)
    for zone, feature in enumerate(data["features"], start=1):
        for ring in rings(feature["geometry"]):
            polygon = [
                (x0 + (p[0] - min_lon) / (max_lon - min_lon) * (x1 - x0),
                 y0 + (max_lat - p[1]) / (max_lat - min_lat) * (y1 - y0))
                for p in ring
            ]
            draw.polygon(polygon, fill=zone)
    guide = np.asarray(image).copy()
    guide[~mask] = -1
    return guide


def partition(mask, guide, seeds):
    owner = np.full(mask.shape, -1, dtype=np.int16)
    distance = np.full(mask.shape, np.inf)
    queue = []
    for i, (_, x, y, _) in enumerate(seeds):
        owner[y, x] = i
        distance[y, x] = 0
        heapq.heappush(queue, (0, i, x, y))
    moves = [(-1, 0, 10), (1, 0, 10), (0, -1, 10), (0, 1, 10),
             (-1, -1, 14), (-1, 1, 14), (1, -1, 14), (1, 1, 14)]
    while queue:
        cost, source, x, y = heapq.heappop(queue)
        if cost != distance[y, x] or owner[y, x] != source:
            continue
        for dx, dy, step in moves:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0] and mask[ny, nx]):
                continue
            crossing = guide[y, x] > 0 and guide[ny, nx] > 0 and guide[y, x] != guide[ny, nx]
            new = cost + step + (28 if crossing else 0)
            if new < distance[ny, nx]:
                distance[ny, nx] = new
                owner[ny, nx] = source
                heapq.heappush(queue, (new, source, nx, ny))
    return owner


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = np.asarray(Image.open(SOURCE).convert("RGB"))
    mask = np.all(source == BEIJING_COLOR, axis=2)
    y0, x0 = np.min(np.argwhere(mask), axis=0)
    y1, x1 = np.max(np.argwhere(mask), axis=0)
    seeds = [(name, *snap(mask, x, y), color) for name, x, y, color in PROVINCES]
    guide = geo_guide(mask, x0, y0, x1, y1)
    owner = partition(mask, guide, seeds)
    draft = source.copy()
    for i, (_, _, _, color) in enumerate(seeds):
        draft[owner == i] = color
    assert np.array_equal(draft[~mask], source[~mask])

    Image.fromarray(draft).save(OUT / "beijing_yandu_5_full_draft.bmp")
    pad = 5
    cx0, cy0, cx1, cy1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    crop = draft[cy0:cy1 + 1, cx0:cx1 + 1]
    Image.fromarray(crop).save(OUT / "beijing_yandu_5_draft.bmp")
    scale = 14
    raw = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    raw.save(OUT / "beijing_yandu_5_raw.png")

    local = draft[cy0:cy1 + 1, cx0:cx1 + 1]
    local_mask = mask[cy0:cy1 + 1, cx0:cx1 + 1]
    boundary = np.zeros(local_mask.shape, dtype=bool)
    boundary[1:] |= local_mask[1:] & np.any(local[1:] != local[:-1], axis=2)
    boundary[:, 1:] |= local_mask[:, 1:] & np.any(local[:, 1:] != local[:, :-1], axis=2)
    display = np.asarray(raw).copy()
    display[np.repeat(np.repeat(boundary, scale, 0), scale, 1)] = (35, 35, 35)
    map_image = Image.fromarray(display)

    canvas = Image.new("RGB", (map_image.width + 390, max(map_image.height, 600)), "white")
    canvas.paste(map_image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 22)
    small = ImageFont.truetype(font_path, 17)
    number = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 18)
    lx = map_image.width + 24
    draw.text((lx, 24), "燕都区域：北京五省草案", fill=(20, 20, 20), font=title)
    draw.text((lx, 65), "现有外轮廓锁定；GeoJSON 区县引导", fill=(80, 80, 80), font=small)
    for i, (name, sx, sy, color) in enumerate(seeds, start=1):
        ty = 115 + (i - 1) * 58
        draw.rectangle((lx, ty + 3, lx + 29, ty + 32), fill=color, outline=(35, 35, 35))
        draw.text((lx + 42, ty), f"{i:02d}  {name}", fill=(20, 20, 20), font=body)
        px, py = (sx - cx0) * scale + 2, (sy - cy0) * scale - 4
        draw.text((px, py), str(i), fill="black", font=number, stroke_width=3, stroke_fill="white")
    draw.text((lx, 440), "区域名：燕都", fill=(45, 45, 45), font=body)
    draw.text((lx, 486), "外部边界改动：0 像素", fill=(70, 70, 70), font=small)
    draw.text((lx, 515), "未写入正式 provinces.bmp", fill=(70, 70, 70), font=small)
    canvas.save(OUT / "beijing_yandu_5_annotated.png")
    print("YANDU_DRAFT:5; OUTSIDE_CHANGED:0")


if __name__ == "__main__":
    main()
