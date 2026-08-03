#!/usr/bin/env python3
"""Render a 23-province Hebei preview while preserving the current Yandu."""

import colorsys
import heapq
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "guangdong_independent_practice/map/provinces.bmp"
GEO_DIR = ROOT / "planning/hebei/geojson_cities"
OUT = ROOT / "planning/hebei"

HEBEI_COLORS = {
    (227, 142, 0), (99, 144, 64), (228, 158, 192), (124, 210, 144),
    (143, 75, 75), (94, 52, 48), (151, 185, 125),
}

# Historical seat, approximate longitude/latitude, and proposed area.
PROVINCES = [
    ("宣府", 114.88, 40.82, "宣镇"), ("万全", 114.73, 40.77, "宣镇"),
    ("蔚州", 114.59, 39.84, "宣镇"), ("怀来", 115.52, 40.40, "宣镇"),
    ("承德", 117.94, 40.98, "燕北"), ("兴州", 117.34, 40.94, "燕北"),
    ("遵化", 117.96, 40.19, "燕北"),
    ("永平", 118.89, 39.89, "永平"), ("滦州", 118.70, 39.74, "永平"),
    ("山海关", 119.77, 40.00, "永平"),
    ("保定", 115.46, 38.87, "保河"), ("易州", 115.50, 39.35, "保河"),
    ("河间", 116.10, 38.44, "保河"), ("沧州", 116.84, 38.30, "保河"),
    ("真定", 114.57, 38.15, "恒赵"), ("定州", 114.99, 38.52, "恒赵"),
    ("赵州", 114.78, 37.75, "恒赵"), ("井陉", 114.14, 38.03, "恒赵"),
    ("邢州", 114.50, 37.07, "冀南"), ("广平", 114.95, 36.48, "冀南"),
    ("大名", 115.15, 36.28, "冀南"), ("冀州", 115.58, 37.55, "冀南"),
    ("深州", 115.55, 38.00, "冀南"),
]


def packed_mask(arr, colours):
    packed = (arr[:, :, 0].astype(np.uint32) << 16) | (arr[:, :, 1].astype(np.uint32) << 8) | arr[:, :, 2]
    keys = np.array([(r << 16) | (g << 8) | b for r, g, b in colours], dtype=np.uint32)
    return np.isin(packed, keys)


def rings(geometry):
    if geometry["type"] == "Polygon":
        yield from geometry["coordinates"]
    else:
        for polygon in geometry["coordinates"]:
            yield from polygon


def load_features():
    features = []
    for path in sorted(GEO_DIR.glob("*_full.json")):
        features.extend(json.loads(path.read_text())["features"])
    return features


def geo_bounds(features):
    points = [p for feature in features for ring in rings(feature["geometry"]) for p in ring]
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def project(lon, lat, bounds, box):
    min_lon, min_lat, max_lon, max_lat = bounds
    x0, y0, x1, y1 = box
    x = x0 + (lon - min_lon) / (max_lon - min_lon) * (x1 - x0)
    y = y0 + (max_lat - lat) / (max_lat - min_lat) * (y1 - y0)
    return int(round(x)), int(round(y))


def snap(mask, x, y):
    if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1] and mask[y, x]:
        return x, y
    yy, xx = np.nonzero(mask)
    i = np.argmin((xx - x) ** 2 + (yy - y) ** 2)
    return int(xx[i]), int(yy[i])


def raster_guide(features, bounds, box, mask):
    image = Image.new("I", (mask.shape[1], mask.shape[0]), 0)
    draw = ImageDraw.Draw(image)
    for zone, feature in enumerate(features, start=1):
        for ring in rings(feature["geometry"]):
            polygon = [project(p[0], p[1], bounds, box) for p in ring]
            if len(polygon) >= 3:
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
            new = cost + step + (34 if crossing else 0)
            if new < distance[ny, nx]:
                distance[ny, nx] = new
                owner[ny, nx] = source
                heapq.heappush(queue, (new, source, nx, ny))
    return owner


def palette(count):
    used = set()
    for line in (ROOT / "guangdong_independent_practice/map/definition.csv").read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if fields and fields[0].isdigit():
            used.add(tuple(map(int, fields[1:4])))
    result = []
    i = 0
    while len(result) < count:
        hue = (0.11 + i * 0.61803398875) % 1.0
        sat = 0.54 + 0.08 * (i % 3)
        val = 0.72 + 0.07 * (i % 2)
        colour = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(hue, sat, val))
        if colour not in used and colour not in result:
            result.append(colour)
        i += 1
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = np.asarray(Image.open(SOURCE).convert("RGB"))
    mask = packed_mask(source, HEBEI_COLORS)
    y0, x0 = np.min(np.argwhere(mask), axis=0)
    y1, x1 = np.max(np.argwhere(mask), axis=0)
    features = load_features()
    bounds = geo_bounds(features)
    box = (x0, y0, x1, y1)
    seeds = []
    for name, lon, lat, area in PROVINCES:
        x, y = snap(mask, *project(lon, lat, bounds, box))
        seeds.append((name, x, y, area))
    guide = raster_guide(features, bounds, box, mask)
    owner = partition(mask, guide, seeds)
    colours = palette(len(seeds))
    draft = source.copy()
    for i, colour in enumerate(colours):
        draft[owner == i] = colour
    assert np.array_equal(draft[~mask], source[~mask])
    Image.fromarray(draft).save(OUT / "hebei_geojson_23_full_draft.bmp")

    pad = 7
    cx0, cy0, cx1, cy1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    crop = draft[cy0:cy1 + 1, cx0:cx1 + 1]
    Image.fromarray(crop).save(OUT / "hebei_geojson_23_draft.bmp")
    scale = 7
    raw = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    raw.save(OUT / "hebei_geojson_23_raw.png")

    local_mask = mask[cy0:cy1 + 1, cx0:cx1 + 1]
    boundary = np.zeros(local_mask.shape, dtype=bool)
    boundary[1:] |= local_mask[1:] & np.any(crop[1:] != crop[:-1], axis=2)
    boundary[:, 1:] |= local_mask[:, 1:] & np.any(crop[:, 1:] != crop[:, :-1], axis=2)
    shown = np.asarray(raw).copy()
    shown[np.repeat(np.repeat(boundary, scale, 0), scale, 1)] = (35, 35, 35)
    map_img = Image.fromarray(shown)

    legend_w = 560
    canvas = Image.new("RGB", (map_img.width + legend_w, max(map_img.height, 900)), "white")
    canvas.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 19)
    small = ImageFont.truetype(font_path, 16)
    number = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 16)
    lx = map_img.width + 24
    draw.text((lx, 20), "河北 GeoJSON 历史建制细化（23省）", fill=(20, 20, 20), font=title)
    draw.text((lx, 61), "燕都锁定；市县界引导，山川与政治边界优先", fill=(80, 80, 80), font=small)
    area_order = ["宣镇", "燕北", "永平", "保河", "恒赵", "冀南"]
    ordered = [i for area in area_order for i, seed in enumerate(seeds) if seed[3] == area]
    for order_i, seed_i in enumerate(ordered):
        name, sx, sy, area = seeds[seed_i]
        col = order_i // 12
        row = order_i % 12
        tx = lx + col * 255
        ty = 105 + row * 48
        draw.rectangle((tx, ty + 3, tx + 25, ty + 28), fill=colours[seed_i], outline=(35, 35, 35))
        draw.text((tx + 34, ty), f"{seed_i + 1:02d} {name} · {area}", fill=(25, 25, 25), font=body)
        px, py = (sx - cx0) * scale, (sy - cy0) * scale
        draw.text((px, py), str(seed_i + 1), fill="black", font=number, stroke_width=3, stroke_fill="white")
    draw.text((lx, 705), "六区域：宣镇、燕北、永平、保河、恒赵、冀南", fill=(55, 55, 55), font=small)
    draw.text((lx, 735), "燕都五省及周边省份未改动", fill=(55, 55, 55), font=small)
    draw.text((lx, 765), "未写入正式 provinces.bmp", fill=(55, 55, 55), font=small)
    canvas.save(OUT / "hebei_geojson_23_annotated.png")
    print(f"HEBEI_DRAFT:23; PIXELS:{int(mask.sum())}; OUTSIDE_CHANGED:0")


if __name__ == "__main__":
    main()
