#!/usr/bin/env python3
"""Render a Shandong-only historical subdivision preview."""

import heapq
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "guangdong_independent_practice/map/provinces.bmp"
OUT = ROOT / "planning/shandong"
GEOJSON_DIR = OUT / "geojson_cities"

# Existing Shandong mainland colours. The union is the immutable outer border.
SHANDONG_COLOURS = {
    (98, 132, 0),       # Shandong Bandao
    (226, 134, 64),     # Jinan
    (86, 118, 240),     # Wuding (original province 2138)
    (145, 24, 24),      # Laizhou
    (238, 254, 148),    # Yanzhou
}

# Layout follows Ming-era prefectural geography, with two deliberately generous
# core provinces for Zibo/Linzi and Qufu.
SEEDS = [
    ("临清", 4618, 778),
    ("德州", 4635, 773),
    ("武定", 4654, 776),
    ("东昌", 4625, 792),
    ("济南", 4642, 791),
    ("淄博（临淄）", 4658, 791),
    ("青州", 4670, 792),
    ("莱州", 4685, 781),
    ("登州", 4704, 770),
    ("宁海", 4697, 787),
    ("胶州", 4685, 799),
    ("泰安", 4647, 802),
    ("兖州", 4635, 810),
    ("曲阜", 4648, 812),
    ("济宁", 4625, 817),
    ("曹州", 4610, 814),
    ("沂州", 4662, 814),
]

PALETTE = [
    (201, 79, 74), (78, 121, 189), (106, 168, 79), (190, 122, 54),
    (128, 95, 170), (220, 151, 43), (55, 157, 176), (215, 106, 157),
    (139, 121, 88), (70, 175, 128), (170, 91, 187), (57, 105, 200),
    (214, 128, 77), (79, 142, 91), (202, 84, 118), (112, 133, 55),
    (48, 148, 164),
]


def mask_for(arr, colours):
    packed = (arr[:, :, 0].astype(np.uint32) << 16) | (arr[:, :, 1].astype(np.uint32) << 8) | arr[:, :, 2]
    keys = np.array([(r << 16) | (g << 8) | b for r, g, b in colours], dtype=np.uint32)
    return np.isin(packed, keys)


def snap(mask, x, y):
    if mask[y, x]:
        return x, y
    yy, xx = np.nonzero(mask)
    i = np.argmin((xx - x) ** 2 + (yy - y) ** 2)
    return int(xx[i]), int(yy[i])


def iter_rings(geometry):
    if geometry["type"] == "Polygon":
        yield from geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        for polygon in geometry["coordinates"]:
            yield from polygon


def county_guide(region, x0, y0, x1, y1):
    """Rasterize modern county polygons as a soft internal-boundary guide."""
    features = []
    all_points = []
    for path in sorted(GEOJSON_DIR.glob("*_full.json")):
        data = json.loads(path.read_text())
        for feature in data["features"]:
            features.append(feature)
            for ring in iter_rings(feature["geometry"]):
                all_points.extend(ring)
    lon = [p[0] for p in all_points]
    lat = [p[1] for p in all_points]
    min_lon, max_lon = min(lon), max(lon)
    min_lat, max_lat = min(lat), max(lat)

    guide_img = Image.new("I", (region.shape[1], region.shape[0]), 0)
    draw = ImageDraw.Draw(guide_img)
    for zone_id, feature in enumerate(features, start=1):
        for ring in iter_rings(feature["geometry"]):
            pts = [
                (
                    x0 + (p[0] - min_lon) / (max_lon - min_lon) * (x1 - x0),
                    y0 + (max_lat - p[1]) / (max_lat - min_lat) * (y1 - y0),
                )
                for p in ring
            ]
            if len(pts) >= 3:
                draw.polygon(pts, fill=zone_id)
    guide = np.asarray(guide_img, dtype=np.int32).copy()
    guide[~region] = -1
    return guide


def guided_partition(region, guide, seeds):
    """Multi-source path growth; crossing a GeoJSON county edge costs more."""
    height, width = region.shape
    owner = np.full((height, width), -1, dtype=np.int16)
    dist = np.full((height, width), np.inf)
    queue = []
    for i, (_, sx, sy) in enumerate(seeds):
        owner[sy, sx] = i
        dist[sy, sx] = 0.0
        heapq.heappush(queue, (0.0, i, sx, sy))

    neighbours = [(-1, 0, 10), (1, 0, 10), (0, -1, 10), (0, 1, 10),
                  (-1, -1, 14), (-1, 1, 14), (1, -1, 14), (1, 1, 14)]
    while queue:
        cost, seed_i, x, y = heapq.heappop(queue)
        if cost != dist[y, x] or owner[y, x] != seed_i:
            continue
        for dx, dy, step in neighbours:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height and region[ny, nx]):
                continue
            # County lines are suggestions, not walls. This keeps historical units
            # in charge while making their edges follow real geographic bends.
            crossing = guide[y, x] > 0 and guide[ny, nx] > 0 and guide[y, x] != guide[ny, nx]
            new_cost = cost + step + (32 if crossing else 0)
            if new_cost < dist[ny, nx]:
                dist[ny, nx] = new_cost
                owner[ny, nx] = seed_i
                heapq.heappush(queue, (new_cost, seed_i, nx, ny))
    return owner


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = np.asarray(Image.open(SOURCE).convert("RGB"))
    region = mask_for(src, SHANDONG_COLOURS)
    snapped = []
    for name, sx, sy in SEEDS:
        sx, sy = snap(region, sx, sy)
        snapped.append((name, sx, sy))

    y0_raw, x0_raw = np.min(np.argwhere(region), axis=0)
    y1_raw, x1_raw = np.max(np.argwhere(region), axis=0)
    guide = county_guide(region, x0_raw, y0_raw, x1_raw, y1_raw)
    owner = guided_partition(region, guide, snapped)

    draft = src.copy()
    for i, colour in enumerate(PALETTE):
        draft[owner == i] = colour

    # Non-negotiable safety property: not one pixel outside existing Shandong changes.
    assert np.array_equal(draft[~region], src[~region])
    Image.fromarray(draft).save(OUT / "shandong_geojson_historical_17_full_draft.bmp")

    y0, x0 = np.min(np.argwhere(region), axis=0)
    y1, x1 = np.max(np.argwhere(region), axis=0)
    pad = 5
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(src.shape[1] - 1, x1 + pad), min(src.shape[0] - 1, y1 + pad)
    crop = draft[y0:y1 + 1, x0:x1 + 1]
    Image.fromarray(crop).save(OUT / "shandong_geojson_historical_17_draft.bmp")

    scale = 10
    raw = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    raw.save(OUT / "shandong_geojson_historical_17_raw.png")

    # Presentation copy: black internal borders, seed numbers, and a legend.
    local_region = region[y0:y1 + 1, x0:x1 + 1]
    local = draft[y0:y1 + 1, x0:x1 + 1]
    boundary = np.zeros(local_region.shape, dtype=bool)
    boundary[1:, :] |= local_region[1:, :] & np.any(local[1:, :] != local[:-1, :], axis=2)
    boundary[:, 1:] |= local_region[:, 1:] & np.any(local[:, 1:] != local[:, :-1], axis=2)
    p = np.asarray(raw).copy()
    p[np.repeat(np.repeat(boundary, scale, 0), scale, 1)] = (35, 35, 35)
    map_img = Image.fromarray(p)

    legend_w = 455
    canvas = Image.new("RGB", (map_img.width + legend_w, max(map_img.height, 760)), "white")
    canvas.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    cn_font = "/System/Library/Fonts/STHeiti Medium.ttc"
    num_font = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
    title = ImageFont.truetype(cn_font, 27)
    body = ImageFont.truetype(cn_font, 20)
    small = ImageFont.truetype(cn_font, 16)
    number = ImageFont.truetype(num_font, 17)
    lx = map_img.width + 22
    draw.text((lx, 20), "山东 GeoJSON 细化草案（17省）", fill=(20, 20, 20), font=title)
    draw.text((lx, 58), "县界引导；齐鲁双核：淄博与曲阜", fill=(85, 85, 85), font=small)
    for i, ((name, _, _), colour) in enumerate(zip(snapped, PALETTE)):
        ty = 100 + i * 35
        draw.rectangle((lx, ty + 3, lx + 24, ty + 27), fill=colour, outline=(40, 40, 40))
        draw.text((lx + 34, ty), f"{i + 1:02d}  {name}", fill=(25, 25, 25), font=body)

    for i, (_, sx, sy) in enumerate(snapped, start=1):
        px, py = (sx - x0) * scale + 2, (sy - y0) * scale - 3
        label = str(i)
        box = draw.textbbox((px, py), label, font=number, stroke_width=2)
        draw.rectangle((box[0] - 2, box[1] - 1, box[2] + 2, box[3] + 1), fill="white")
        draw.text((px, py), label, fill="black", font=number)

    draw.text((lx, 710), "山东外部边界改动：0 像素", fill=(55, 55, 55), font=small)
    draw.text((lx, 735), "未写入正式 provinces.bmp", fill=(55, 55, 55), font=small)
    canvas.save(OUT / "shandong_geojson_historical_17_annotated.png")

    outside = int(np.count_nonzero(np.any(draft[~region] != src[~region], axis=1)))
    sizes = {name: int(np.count_nonzero(owner == i)) for i, (name, _, _) in enumerate(snapped)}
    print(f"Shandong pixels: {int(region.sum())}")
    print(f"outside changed pixels: {outside}")
    print(f"Zibo pixels: {sizes['淄博（临淄）']}; Qufu pixels: {sizes['曲阜']}")


if __name__ == "__main__":
    main()
